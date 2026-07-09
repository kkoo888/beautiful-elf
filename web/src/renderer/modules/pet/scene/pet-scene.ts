import * as THREE from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'

// ════════════════════════════════════════════════════════════
// 常量
// ════════════════════════════════════════════════════════════

const LOAD_TIMEOUT_MS = 10_000
const FPS_VISIBLE = 60
const FPS_HIDDEN = 5
const CAMERA_PADDING = 1.2
const MOUSE_LERP = 0.08
const MOUSE_CONVERGE_THRESHOLD = 0.001
const DELTA_CLAMP = 0.1 // 最大帧间隔 100ms，防止隐藏后跳帧
const SHADOW_MAP_SIZE = 512 // 桌面宠物 400x500 窗口，512 足够
const HEAD_BONE_NAMES = ['頭', 'head', 'Head', '頭部']
const EYE_BONE_NAMES = ['左目', '右目', 'leftEye', 'rightEye', 'Eye_L', 'Eye_R']

export type LoadProgressCallback = (progress: number, status: string) => void

// ════════════════════════════════════════════════════════════
// PetScene
// ════════════════════════════════════════════════════════════

/**
 * 宠物 3D 场景
 *
 * 管线阶段：
 *   Stage 1: 资产加载（Loader 初始化、模型/动画加载）
 *   Stage 2: 场景构建（材质管线、骨骼查找、阴影地面、相机适配）
 *   Stage 3: 渲染执行（帧循环、OrbitControls、鼠标追踪、截图）
 */
export class PetScene {
  private container: HTMLElement

  // ── Stage 1: 资产 ──
  private loader: any = null
  private helper: any = null
  private hasAnimation = false // 有 VMD 动画时才更新 helper
  private currentModelPath: string | null = null
  private currentVmdPath: string | null = null

  // ── Stage 2: 场景 ──
  private renderer: THREE.WebGLRenderer | null = null
  private scene: THREE.Scene | null = null
  private camera: THREE.PerspectiveCamera | null = null
  private controls: OrbitControls | null = null
  private controlsActive = false // OrbitControls 交互中才更新
  private mesh: THREE.SkinnedMesh | null = null
  private ground: THREE.Mesh | null = null // 动态阴影地面
  private clock: THREE.Clock | null = null
  private _isLoaded = false

  // ── Stage 3: 渲染 ──
  private animationId: number | null = null
  private visible = true
  private lastFrameTime = 0
  private fpsInterval = 1000 / FPS_VISIBLE
  private contextLost = false
  private contextLostHandler: (() => void) | null = null
  private contextRestoredHandler: (() => void) | null = null

  // ── 鼠标追踪（dirty flag 优化） ──
  private mouseX = 0
  private mouseY = 0
  private mouseDirty = false
  private headBone: THREE.Bone | null = null
  private eyeBones: THREE.Bone[] = []
  private headRestRotation = new THREE.Euler()
  private eyeRestRotations: THREE.Euler[] = []

  constructor(container: HTMLElement) {
    this.container = container
  }

  get isLoaded(): boolean {
    return this._isLoaded
  }

  // ══════════════════════════════════════════════════════════
  // Stage 1: 资产加载
  // ══════════════════════════════════════════════════════════

  /** 初始化场景、灯光、相机、Controls、Loader */
  async init(): Promise<void> {
    const width = this.container.clientWidth
    const height = this.container.clientHeight

    // 渲染器
    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
    this.renderer.setSize(width, height)
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    this.renderer.outputColorSpace = THREE.SRGBColorSpace
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping
    this.renderer.toneMappingExposure = 1.0
    this.renderer.shadowMap.enabled = true
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap
    this.container.appendChild(this.renderer.domElement)
    this.setupContextLossHandlers()

    // 场景
    this.scene = new THREE.Scene()

    // 相机
    this.camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000)
    this.camera.position.set(0, 12, 25)
    this.camera.lookAt(0, 10, 0)

    // OrbitControls（交互时才更新）
    this.controls = new OrbitControls(this.camera, this.renderer.domElement)
    this.controls.target.set(0, 10, 0)
    this.controls.enableDamping = true
    this.controls.dampingFactor = 0.05
    this.controls.enableZoom = false
    this.controls.mouseButtons = {
      LEFT: undefined as unknown as THREE.MOUSE,
      MIDDLE: THREE.MOUSE.DOLLY,
      RIGHT: THREE.MOUSE.ROTATE,
    }
    this.controls.addEventListener('start', () => { this.controlsActive = true })
    this.controls.addEventListener('end', () => { this.controlsActive = false })

    // 灯光（4 灯配置）
    this.setupLights()

    // 时钟 + 丢弃首帧 delta
    this.clock = new THREE.Clock()
    this.clock.getDelta()

    // Loader（动态 import）
    await this.setupLoaders()

    window.addEventListener('resize', this.handleResize)
    this.startRenderLoop()
  }

  /** 4 灯配置：环境光 + 半球光 + 主定向光（阴影）+ 补光 + 轮廓光 */
  private setupLights(): void {
    if (!this.scene) return

    // 环境光
    this.scene.add(new THREE.AmbientLight(0xffffff, 0.6))

    // 半球光（天空/地面渐变）
    this.scene.add(new THREE.HemisphereLight(0xddeeff, 0x202020, 0.5))

    // 主定向光 + 阴影（512 足够桌面宠物）
    const dirLight = new THREE.DirectionalLight(0xffffff, 1.2)
    dirLight.position.set(20, 50, 30)
    dirLight.castShadow = true
    dirLight.shadow.mapSize.width = SHADOW_MAP_SIZE
    dirLight.shadow.mapSize.height = SHADOW_MAP_SIZE
    dirLight.shadow.bias = -0.0001
    dirLight.shadow.normalBias = 0.05
    this.scene.add(dirLight)

    // 补光灯（暖色柔化阴影）
    const fillLight = new THREE.DirectionalLight(0xffeedd, 0.4)
    fillLight.position.set(-20, 20, 20)
    this.scene.add(fillLight)

    // 轮廓光（背光分离）
    const rimLight = new THREE.SpotLight(0xffffff, 0.8)
    rimLight.position.set(0, 40, -30)
    rimLight.lookAt(0, 10, 0)
    this.scene.add(rimLight)
  }

  /** 动态加载 MMDLoader + MMDAnimationHelper */
  private async setupLoaders(): Promise<void> {
    try {
      const mod = await import('three/examples/jsm/loaders/MMDLoader.js')
      this.loader = new mod.MMDLoader()
    } catch (e) {
      console.warn('[PetScene] MMDLoader import failed:', e)
    }

    try {
      const mod = await import('three/examples/jsm/animation/MMDAnimationHelper.js')
      this.helper = new mod.MMDAnimationHelper({
        afterglow: 2.0,
        resetPhysicsOnLoop: true,
      })
    } catch (e) {
      console.warn('[PetScene] MMDAnimationHelper import failed:', e)
    }
  }

  /** 加载 PMX 模型（无动画） */
  async loadModel(modelPath: string, onProgress?: LoadProgressCallback): Promise<void> {
    if (!this.scene || !this.loader) return
    onProgress?.(0, '加载模型中...')

    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => reject(new Error(`加载超时: ${modelPath}`)), LOAD_TIMEOUT_MS)

      this.loader.load(
        modelPath,
        (mesh: THREE.SkinnedMesh) => {
          clearTimeout(timeout)
          this.hasAnimation = false
          this.applyModel(mesh)
          this.currentModelPath = modelPath
          this.currentVmdPath = null
          onProgress?.(100, '模型加载完成')
          resolve()
        },
        (progress: ProgressEvent) => {
          if (progress.total > 0) onProgress?.(Math.round(progress.loaded / progress.total * 100), '加载中')
        },
        (error: unknown) => {
          clearTimeout(timeout)
          reject(error instanceof Error ? error : new Error(String(error)))
        },
      )
    })
  }

  /** 加载 PMX 模型 + VMD 动画 */
  async loadModelWithAnimation(
    modelPath: string,
    vmdPath: string,
    onProgress?: LoadProgressCallback,
  ): Promise<void> {
    if (!this.scene || !this.loader) return
    onProgress?.(0, '加载模型+动画中...')

    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => reject(new Error(`加载超时: ${modelPath}`)), LOAD_TIMEOUT_MS)

      this.loader.loadWithAnimation(
        modelPath,
        vmdPath,
        (result: { mesh: THREE.SkinnedMesh; animation: THREE.AnimationClip }) => {
          clearTimeout(timeout)
          this.applyModel(result.mesh)

          if (this.helper) {
            try {
              this.helper.add(result.mesh, { animation: result.animation, physics: true })
              this.hasAnimation = true
            } catch (e) {
              console.warn('[PetScene] helper.add failed:', e)
            }
          }

          this.currentModelPath = modelPath
          this.currentVmdPath = vmdPath
          onProgress?.(100, '模型+动画加载完成')
          resolve()
        },
        (progress: ProgressEvent) => {
          if (progress.total > 0) onProgress?.(Math.round(progress.loaded / progress.total * 100), '加载中')
        },
        (error: unknown) => {
          clearTimeout(timeout)
          reject(error instanceof Error ? error : new Error(String(error)))
        },
      )
    })
  }

  /** 重新加载当前模型 */
  async reloadModel(onProgress?: LoadProgressCallback): Promise<void> {
    if (!this.currentModelPath) return
    if (this.currentVmdPath) {
      await this.loadModelWithAnimation(this.currentModelPath, this.currentVmdPath, onProgress)
    } else {
      await this.loadModel(this.currentModelPath, onProgress)
    }
  }

  // ══════════════════════════════════════════════════════════
  // Stage 2: 场景构建（材质管线 + 骨骼 + 地面 + 相机）
  // ══════════════════════════════════════════════════════════

  /**
   * 统一的模型应用管线：
   *   1. 清理旧模型
   *   2. 材质管线（保留 toon / 转 PBR）
   *   3. 阴影
   *   4. 添加到场景
   *   5. 动态阴影地面
   *   6. 相机适配
   *   7. 骨骼缓存
   */
  private applyModel(mesh: THREE.SkinnedMesh): void {
    // 1. 清理旧模型
    this.disposeCurrentMesh()

    // 2. 材质管线
    this.materialPipeline(mesh)

    // 3. 阴影
    mesh.castShadow = true
    mesh.receiveShadow = true

    this._isLoaded = false
    this.mesh = mesh

    // 4. 添加到场景
    this.scene!.add(mesh)

    // 5. 动态阴影地面（基于模型 bbox）
    this.updateGroundPlane(mesh)

    // 6. 相机适配
    this.fitCameraToModel(mesh)

    // 7. 骨骼缓存
    this.findHeadAndEyeBones()
  }

  /** 材质管线：保留 toon 风格 / Phong→PBR / 通用回退 */
  private materialPipeline(mesh: THREE.SkinnedMesh): void {
    const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material]

    const result = materials.map((mat) => {
      if (mat instanceof THREE.MeshStandardMaterial) {
        mat.skinning = true
        return mat
      }
      // MMDLoader 的 toon 材质 → 保留（卡通风格核心）
      if (mat instanceof THREE.MeshToonMaterial) {
        mat.skinning = true
        mat.needsUpdate = true
        return mat
      }
      // Phong → PBR
      if (mat instanceof THREE.MeshPhongMaterial) {
        const pbr = new THREE.MeshStandardMaterial()
        pbr.map = mat.map
        pbr.normalMap = mat.normalMap
        pbr.emissiveMap = mat.emissiveMap
        pbr.emissive = mat.emissive
        pbr.emissiveIntensity = mat.emissiveIntensity
        pbr.transparent = mat.transparent
        pbr.opacity = mat.opacity
        pbr.side = mat.side
        pbr.alphaTest = mat.alphaTest
        pbr.skinning = true
        pbr.roughness = mat.shininess > 0 ? Math.max(0.2, 1.0 - mat.shininess / 100) : 0.6
        pbr.metalness = 0.1
        pbr.needsUpdate = true
        mat.dispose()
        return pbr
      }
      // 通用回退 → PBR
      const pbr = new THREE.MeshStandardMaterial()
      pbr.map = (mat as any).map ?? null
      pbr.transparent = mat.transparent
      pbr.opacity = mat.opacity
      pbr.side = mat.side
      pbr.alphaTest = mat.alphaTest
      pbr.skinning = true
      pbr.roughness = 0.5
      pbr.metalness = 0.1
      pbr.needsUpdate = true
      mat.dispose()
      return pbr
    })

    mesh.material = result.length === 1 ? result[0] : result
  }

  /** 动态阴影地面：根据模型 bbox 自动调整大小 */
  private updateGroundPlane(mesh: THREE.SkinnedMesh): void {
    if (!this.scene) return

    // 移除旧地面
    if (this.ground) {
      this.scene.remove(this.ground)
      this.ground.geometry.dispose()
    }

    const box = new THREE.Box3().setFromObject(mesh)
    const size = box.getSize(new THREE.Vector3())
    const center = box.getCenter(new THREE.Vector3())
    const groundSize = Math.max(size.x, size.z) * CAMERA_PADDING * 3

    const geo = new THREE.PlaneGeometry(groundSize, groundSize)
    const mat = new THREE.ShadowMaterial({ opacity: 0.3 })
    this.ground = new THREE.Mesh(geo, mat)
    this.ground.rotation.x = -Math.PI / 2
    this.ground.position.y = box.min.y
    this.ground.receiveShadow = true
    this.scene.add(this.ground)
  }

  /** 相机适配（带 padding） */
  private fitCameraToModel(mesh: THREE.SkinnedMesh): void {
    if (!this.camera) return

    const box = new THREE.Box3().setFromObject(mesh)
    const center = box.getCenter(new THREE.Vector3())
    const size = box.getSize(new THREE.Vector3())
    const maxDim = Math.max(size.x, size.y, size.z, 0.1)
    const fov = this.camera.fov * (Math.PI / 180)
    const distance = Math.max((maxDim * CAMERA_PADDING) / (2 * Math.tan(fov / 2)), 5)

    this.camera.position.set(center.x, center.y, center.z + distance * 1.5)
    this.camera.lookAt(center)
  }

  /** 缓存头部/眼球骨骼引用 */
  private findHeadAndEyeBones(): void {
    this.headBone = null
    this.eyeBones = []
    this.eyeRestRotations = []
    if (!this.mesh) return

    this.mesh.traverse((child) => {
      if (!(child instanceof THREE.Bone)) return
      const name = child.name

      if (!this.headBone && HEAD_BONE_NAMES.some((n) => name.includes(n))) {
        this.headBone = child
        this.headRestRotation.copy(child.rotation)
      }

      if (EYE_BONE_NAMES.some((n) => name.includes(n))) {
        this.eyeBones.push(child)
        this.eyeRestRotations.push(child.rotation.clone())
      }
    })
  }

  // ══════════════════════════════════════════════════════════
  // Stage 3: 渲染执行
  // ══════════════════════════════════════════════════════════

  private startRenderLoop(): void {
    const animate = (timestamp: number): void => {
      this.animationId = requestAnimationFrame(animate)

      const elapsed = timestamp - this.lastFrameTime
      if (elapsed < this.fpsInterval) return
      this.lastFrameTime = timestamp

      if (this.contextLost || !this.renderer || !this.scene || !this.camera) return

      // delta clamp：防止隐藏后跳帧
      const delta = Math.min(this.clock!.getDelta(), DELTA_CLAMP)

      // OrbitControls：只在交互中更新
      if (this.controlsActive) {
        this.controls?.update()
      }

      // 动画：只在有 VMD 动画时更新
      if (this.helper && this.hasAnimation) {
        try { this.helper.update(delta) } catch { /* ignore */ }
      }

      // 鼠标追踪：只在鼠标移动时更新
      if (this.mouseDirty) {
        this.updateMouseLook()
      }

      try { this.renderer.render(this.scene, this.camera) } catch { /* ignore */ }
    }

    this.animationId = requestAnimationFrame(animate)
  }

  /** 鼠标追踪（dirty flag + 收敛检测） */
  private updateMouseLook(): void {
    if (!this.mesh || (!this.headBone && this.eyeBones.length === 0)) {
      this.mouseDirty = false
      return
    }

    const targetYaw = this.mouseX * 0.44
    const targetPitch = -this.mouseY * 0.26

    let converged = true

    // 头部跟随
    if (this.headBone) {
      const newYaw = THREE.MathUtils.lerp(this.headBone.rotation.y, this.headRestRotation.y + targetYaw, MOUSE_LERP)
      const newPitch = THREE.MathUtils.lerp(this.headBone.rotation.x, this.headRestRotation.x + targetPitch, MOUSE_LERP)
      if (Math.abs(newYaw - this.headBone.rotation.y) > MOUSE_CONVERGE_THRESHOLD ||
          Math.abs(newPitch - this.headBone.rotation.x) > MOUSE_CONVERGE_THRESHOLD) {
        converged = false
      }
      this.headBone.rotation.y = newYaw
      this.headBone.rotation.x = newPitch
    }

    // 眼球跟随
    const eyeYaw = targetYaw * 0.6
    const eyePitch = targetPitch * 0.6
    for (let i = 0; i < this.eyeBones.length; i++) {
      const bone = this.eyeBones[i]
      const rest = this.eyeRestRotations[i]
      if (!bone || !rest) continue
      const newY = THREE.MathUtils.lerp(bone.rotation.y, rest.y + eyeYaw, MOUSE_LERP * 1.5)
      const newX = THREE.MathUtils.lerp(bone.rotation.x, rest.x + eyePitch, MOUSE_LERP * 1.5)
      if (Math.abs(newY - bone.rotation.y) > MOUSE_CONVERGE_THRESHOLD ||
          Math.abs(newX - bone.rotation.x) > MOUSE_CONVERGE_THRESHOLD) {
        converged = false
      }
      bone.rotation.y = newY
      bone.rotation.x = newX
    }

    // 收敛后停止每帧计算
    if (converged) this.mouseDirty = false
  }

  // ══════════════════════════════════════════════════════════
  // 公共 API
  // ══════════════════════════════════════════════════════════

  /** 设置鼠标坐标（IPC 调用） */
  setMousePosition(normalizedX: number, normalizedY: number): void {
    if (normalizedX !== this.mouseX || normalizedY !== this.mouseY) {
      this.mouseX = normalizedX
      this.mouseY = normalizedY
      this.mouseDirty = true
    }
  }

  /** 设置可见性 */
  setVisible(visible: boolean): void {
    this.visible = visible
    this.fpsInterval = 1000 / (visible ? FPS_VISIBLE : FPS_HIDDEN)
    this.lastFrameTime = 0
  }

  /** 窗口 resize */
  resize(): void {
    const width = this.container.clientWidth
    const height = this.container.clientHeight
    if (width <= 0 || height <= 0) return
    if (this.camera) {
      this.camera.aspect = width / height
      this.camera.updateProjectionMatrix()
    }
    this.renderer?.setSize(width, height)
  }

  /** 获取 canvas */
  getCanvas(): HTMLCanvasElement | null {
    return this.renderer?.domElement ?? null
  }

  /** 异步截图（toBlob，不阻塞渲染线程） */
  getScreenshotDataURL(): string | null {
    const canvas = this.renderer?.domElement
    if (!canvas) return null
    try {
      return canvas.toDataURL('image/png')
    } catch {
      return null
    }
  }

  /** 异步截图（toBlob 回调，推荐用于定时截图） */
  getScreenshotBlob(callback: (dataUrl: string | null) => void): void {
    const canvas = this.renderer?.domElement
    if (!canvas) { callback(null); return }
    try {
      canvas.toBlob((blob) => {
        if (!blob) { callback(null); return }
        const reader = new FileReader()
        reader.onload = () => callback(reader.result as string)
        reader.onerror = () => callback(null)
        reader.readAsDataURL(blob)
      }, 'image/png')
    } catch {
      callback(null)
    }
  }

  // ══════════════════════════════════════════════════════════
  // 内部工具
  // ══════════════════════════════════════════════════════════

  private disposeCurrentMesh(): void {
    if (!this.mesh) return
    this.scene?.remove(this.mesh)
    this.mesh.geometry.dispose()
    const mats = Array.isArray(this.mesh.material) ? this.mesh.material : [this.mesh.material]
    mats.forEach((m) => m.dispose())
    this.mesh = null
  }

  private handleResize = (): void => { this.resize() }

  private setupContextLossHandlers(): void {
    if (!this.renderer) return
    const canvas = this.renderer.domElement
    this.contextLostHandler = (e: Event) => { e.preventDefault(); this.contextLost = true }
    this.contextRestoredHandler = () => { this.contextLost = false; this.lastFrameTime = 0 }
    canvas.addEventListener('webglcontextlost', this.contextLostHandler)
    canvas.addEventListener('webglcontextrestored', this.contextRestoredHandler)
  }

  private removeContextLossHandlers(): void {
    if (!this.renderer) return
    const canvas = this.renderer.domElement
    if (this.contextLostHandler) { canvas.removeEventListener('webglcontextlost', this.contextLostHandler); this.contextLostHandler = null }
    if (this.contextRestoredHandler) { canvas.removeEventListener('webglcontextrestored', this.contextRestoredHandler); this.contextRestoredHandler = null }
  }

  /** 销毁所有资源 */
  dispose(): void {
    window.removeEventListener('resize', this.handleResize)
    this.removeContextLossHandlers()

    if (this.animationId !== null) { cancelAnimationFrame(this.animationId); this.animationId = null }

    this.disposeCurrentMesh()

    if (this.ground) { this.scene?.remove(this.ground); this.ground.geometry.dispose(); this.ground = null }

    this.controls?.dispose()
    this.controls = null
    this.helper?.dispose()
    this.helper = null
    this.renderer?.dispose()
    this.renderer?.domElement.remove()

    this.renderer = null
    this.scene = null
    this.camera = null
    this.clock = null
    this.loader = null
    this._isLoaded = false
  }
}
