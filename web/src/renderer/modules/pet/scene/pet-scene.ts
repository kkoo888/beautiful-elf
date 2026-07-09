import * as THREE from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'

/** 加载超时时间 (ms) */
const LOAD_TIMEOUT_MS = 10_000
/** 可见时帧率 */
const FPS_VISIBLE = 60
/** 不可见时帧率 */
const FPS_HIDDEN = 5
/** 模型边界 padding 系数 */
const CAMERA_PADDING = 1.2
/** 鼠标追踪平滑系数（0-1，越大越快） */
const MOUSE_LERP = 0.08
/** 头部骨骼名称列表（PMX 常见命名） */
const HEAD_BONE_NAMES = ['頭', 'head', 'Head', '頭部']
/** 眼球骨骼名称列表 */
const EYE_BONE_NAMES = ['左目', '右目', 'leftEye', 'rightEye', 'Eye_L', 'Eye_R']

/** 加载进度回调 */
export type LoadProgressCallback = (progress: number, status: string) => void

/**
 * 宠物 3D 场景管理
 * 负责：Three.js 场景初始化、PMX 模型加载、VMD 动画、渲染循环、
 *       OrbitControls 交互、鼠标追踪视线跟随、截图
 *
 * 使用 Three.js r171 官方 MMDLoader（本地模块）
 */
export class PetScene {
  private container: HTMLElement
  private renderer: THREE.WebGLRenderer | null = null
  private scene: THREE.Scene | null = null
  private camera: THREE.PerspectiveCamera | null = null
  private controls: OrbitControls | null = null
  private clock: THREE.Clock | null = null
  private animationId: number | null = null
  private visible = true
  private mesh: THREE.SkinnedMesh | null = null
  private helper: any = null
  private loader: any = null

  /** 当前模型路径（用于 reloadModel） */
  private currentModelPath: string | null = null
  private currentVmdPath: string | null = null

  /** 帧率控制 */
  private lastFrameTime = 0
  private fpsInterval = 1000 / FPS_VISIBLE

  /** 模型是否已成功加载 */
  private _isLoaded = false

  /** WebGL context 丢失标记 */
  private contextLost = false
  private contextLostHandler: (() => void) | null = null
  private contextRestoredHandler: (() => void) | null = null

  // ── 鼠标追踪 ──
  /** 鼠标归一化坐标 (-1 ~ 1) */
  private mouseX = 0
  private mouseY = 0
  /** 头部骨骼引用 */
  private headBone: THREE.Bone | null = null
  /** 眼球骨骼引用 */
  private eyeBones: THREE.Bone[] = []
  /** 头部初始旋转 */
  private headRestRotation = new THREE.Euler()
  /** 眼球初始旋转 */
  private eyeRestRotations: THREE.Euler[] = []

  constructor(container: HTMLElement) {
    this.container = container
  }

  /** 模型是否已加载完成 */
  get isLoaded(): boolean {
    return this._isLoaded
  }

  /** 初始化 Three.js 场景 */
  async init(): Promise<void> {
    const width = this.container.clientWidth
    const height = this.container.clientHeight

    // 渲染器（透明背景）
    this.renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: true,
    })
    this.renderer.setSize(width, height)
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    this.renderer.outputColorSpace = THREE.SRGBColorSpace
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping
    this.renderer.toneMappingExposure = 1.0
    this.renderer.shadowMap.enabled = true
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap
    this.container.appendChild(this.renderer.domElement)

    // WebGL context 丢失/恢复处理
    this.setupContextLossHandlers()

    // 场景
    this.scene = new THREE.Scene()

    // 相机
    this.camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000)
    this.camera.position.set(0, 12, 25)
    this.camera.lookAt(0, 10, 0)

    // ── OrbitControls（右键旋转，左键保留给窗口拖拽） ──
    this.controls = new OrbitControls(this.camera, this.renderer.domElement)
    this.controls.target.set(0, 10, 0)
    this.controls.enableDamping = true
    this.controls.dampingFactor = 0.05
    this.controls.enableZoom = false
    this.controls.mouseButtons = {
      LEFT: null as unknown as THREE.MOUSE,
      MIDDLE: THREE.MOUSE.DOLLY,
      RIGHT: THREE.MOUSE.ROTATE,
    }

    // ── 灯光系统（4 灯配置，参考 PeroCore） ──

    // 环境光 — 基础照明
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6)
    this.scene.add(ambientLight)

    // 半球光 — 自然天空/地面渐变，增加层次感
    const hemiLight = new THREE.HemisphereLight(0xddeeff, 0x202020, 0.5)
    this.scene.add(hemiLight)

    // 主定向光 — 太阳，带阴影
    const dirLight = new THREE.DirectionalLight(0xffffff, 1.2)
    dirLight.position.set(20, 50, 30)
    dirLight.castShadow = true
    dirLight.shadow.mapSize.width = 2048
    dirLight.shadow.mapSize.height = 2048
    dirLight.shadow.bias = -0.0001
    dirLight.shadow.normalBias = 0.05
    this.scene.add(dirLight)

    // 补光灯 — 暖色柔化阴影
    const fillLight = new THREE.DirectionalLight(0xffeedd, 0.4)
    fillLight.position.set(-20, 20, 20)
    this.scene.add(fillLight)

    // 轮廓光 — 背光分离模型与背景
    const rimLight = new THREE.SpotLight(0xffffff, 0.8)
    rimLight.position.set(0, 40, -30)
    rimLight.lookAt(0, 10, 0)
    this.scene.add(rimLight)

    // 阴影地面 — 不可见但接收阴影，给模型"落地感"
    const groundGeo = new THREE.PlaneGeometry(100, 100)
    const groundMat = new THREE.ShadowMaterial({ opacity: 0.3 })
    const ground = new THREE.Mesh(groundGeo, groundMat)
    ground.rotation.x = -Math.PI / 2
    ground.position.y = 0
    ground.receiveShadow = true
    this.scene.add(ground)

    // 时钟
    this.clock = new THREE.Clock()

    // MMD 官方 Loader（动态 import）
    try {
      const mod = await import('three/examples/jsm/loaders/MMDLoader.js')
      this.loader = new mod.MMDLoader()
    } catch (e) {
      console.warn('[PetScene] MMDLoader import failed:', e)
      this.loader = null
    }

    // MMDAnimationHelper（动态 import），失败时降级（无 IK/物理模拟）
    try {
      const mod = await import('three/examples/jsm/animation/MMDAnimationHelper.js')
      this.helper = new mod.MMDAnimationHelper({
        afterglow: 2.0,
        resetPhysicsOnLoop: true,
      })
    } catch (err) {
      console.warn('[PetScene] MMDAnimationHelper init failed:', err)
      this.helper = null
    }

    // 响应窗口大小变化
    window.addEventListener('resize', this.handleResize)

    // 开始渲染循环
    this.startRenderLoop()
  }

  /** 加载 PMX 模型（纯模型，无动画），超时 10s */
  async loadModel(modelPath: string, onProgress?: LoadProgressCallback): Promise<void> {
    if (!this.scene) throw new Error('Scene not initialized')
    if (!this.loader) {
      console.warn('[PetScene] loadModel skipped: MMDLoader not available')
      return
    }

    onProgress?.(0, '加载模型中...')

    return new Promise((resolve, reject) => {
      const timeoutId = setTimeout(() => {
        reject(new Error(`模型加载超时 (${LOAD_TIMEOUT_MS / 1000}s): ${modelPath}`))
      }, LOAD_TIMEOUT_MS)

      this.loader!.load(
        modelPath,
        (mesh: THREE.SkinnedMesh) => {
          clearTimeout(timeoutId)
          this.replaceMesh(mesh)
          this.scene!.add(mesh)
          this.fitCameraToModel(mesh)
          this._isLoaded = true
          this.currentModelPath = modelPath
          onProgress?.(100, '模型加载完成')
          resolve()
        },
        (progress: ProgressEvent) => {
          if (progress.total > 0) {
            const pct = Math.round((progress.loaded / progress.total) * 100)
            onProgress?.(pct, `加载中 ${pct}%`)
          }
        },
        (error: unknown) => {
          clearTimeout(timeoutId)
          reject(error instanceof Error ? error : new Error(String(error)))
        }
      )
    })
  }

  /** 加载 PMX 模型 + VMD 动画（官方 loadWithAnimation），超时 10s */
  async loadModelWithAnimation(
    modelPath: string,
    vmdPath: string,
    onProgress?: LoadProgressCallback,
  ): Promise<void> {
    if (!this.scene) throw new Error('Scene not initialized')
    if (!this.loader) {
      console.warn('[PetScene] loadModelWithAnimation skipped: MMDLoader not available')
      return
    }

    onProgress?.(0, '加载模型+动画中...')

    return new Promise((resolve, reject) => {
      const timeoutId = setTimeout(() => {
        reject(new Error(`模型+动画加载超时 (${LOAD_TIMEOUT_MS / 1000}s): ${modelPath}`))
      }, LOAD_TIMEOUT_MS)

      this.loader!.loadWithAnimation(
        modelPath,
        vmdPath,
        (result: { mesh: THREE.SkinnedMesh; animation: THREE.AnimationClip }) => {
          clearTimeout(timeoutId)

          const { mesh, animation } = result

          this.replaceMesh(mesh)

          if (this.helper) {
            try {
              this.helper.add(mesh, {
                animation,
                physics: true,
              })
            } catch (err) {
              console.warn('[PetScene] helper.add() failed, animation will play without IK/physics:', err)
            }
          }

          this.scene!.add(mesh)
          this.fitCameraToModel(mesh)
          this._isLoaded = true
          this.currentModelPath = modelPath
          this.currentVmdPath = vmdPath
          onProgress?.(100, '模型+动画加载完成')
          resolve()
        },
        (progress: ProgressEvent) => {
          if (progress.total > 0) {
            const pct = Math.round((progress.loaded / progress.total) * 100)
            onProgress?.(pct, `加载中 ${pct}%`)
          }
        },
        (error: unknown) => {
          clearTimeout(timeoutId)
          reject(error instanceof Error ? error : new Error(String(error)))
        }
      )
    })
  }

  /**
   * 重新加载当前模型（不依赖窗口显隐）
   * 如果有 VMD 动画路径，自动加载动画
   */
  async reloadModel(onProgress?: LoadProgressCallback): Promise<void> {
    if (!this.currentModelPath) {
      console.warn('[PetScene] reloadModel skipped: no model loaded')
      return
    }

    if (this.currentVmdPath) {
      await this.loadModelWithAnimation(this.currentModelPath, this.currentVmdPath, onProgress)
    } else {
      await this.loadModel(this.currentModelPath, onProgress)
    }
  }

  /** 替换旧模型（升级材质为 PBR + 启用阴影） */
  private replaceMesh(mesh: THREE.SkinnedMesh): void {
    if (this.mesh) {
      this.scene!.remove(this.mesh)
      this.mesh.geometry.dispose()
      if (Array.isArray(this.mesh.material)) {
        this.mesh.material.forEach((m) => m.dispose())
      } else if (this.mesh.material instanceof THREE.Material) {
        this.mesh.material.dispose()
      }
    }

    // 升级材质为 PBR（MeshStandardMaterial）
    this.upgradeMaterial(mesh)

    // 启用阴影投射/接收
    mesh.castShadow = true
    mesh.receiveShadow = true

    this._isLoaded = false
    this.mesh = mesh

    // 缓存头部/眼球骨骼引用（鼠标追踪用）
    this.findHeadAndEyeBones()
  }

  /** 将模型材质升级为 PBR MeshStandardMaterial */
  private upgradeMaterial(mesh: THREE.SkinnedMesh): void {
    const origMat = mesh.material
    const materials = Array.isArray(origMat) ? origMat : [origMat]

    const upgraded = materials.map((mat) => {
      if (mat instanceof THREE.MeshStandardMaterial) return mat

      const pbr = new THREE.MeshStandardMaterial()

      // 迁移原始材质属性
      if (mat instanceof THREE.MeshPhongMaterial) {
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
        // Phong specular → PBR roughness 近似转换
        pbr.roughness = mat.shininess > 0 ? Math.max(0.2, 1.0 - mat.shininess / 100) : 0.6
        pbr.metalness = 0.1
      } else {
        // 通用回退
        pbr.map = (mat as any).map ?? null
        pbr.transparent = mat.transparent
        pbr.opacity = mat.opacity
        pbr.side = mat.side
        pbr.alphaTest = mat.alphaTest
        pbr.skinning = true
        pbr.roughness = 0.5
        pbr.metalness = 0.1
      }

      pbr.needsUpdate = true
      mat.dispose()
      return pbr
    })

    mesh.material = upgraded.length === 1 ? upgraded[0] : upgraded
  }

  /** 自动调整相机以适配模型（带 padding，让模型有呼吸空间） */
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

  /** 渲染循环（基于时间戳的帧率控制） */
  private startRenderLoop(): void {
    const animate = (timestamp: number): void => {
      this.animationId = requestAnimationFrame(animate)

      const elapsed = timestamp - this.lastFrameTime
      if (elapsed < this.fpsInterval) return
      this.lastFrameTime = timestamp

      if (this.contextLost) return

      if (!this.renderer || !this.scene || !this.camera) return

      const delta = this.clock!.getDelta()

      // 更新 OrbitControls 阻尼
      this.controls?.update()

      if (this.helper) {
        try {
          this.helper.update(delta)
        } catch {
          // helper 更新失败时静默忽略
        }
      }

      // 鼠标追踪：头部/眼球跟随
      this.updateMouseLook()

      try {
        this.renderer.render(this.scene, this.camera)
      } catch {
        // 渲染失败时静默忽略
      }
    }

    this.animationId = requestAnimationFrame(animate)
  }

  /** 设置可见性（控制帧率节省资源） */
  setVisible(visible: boolean): void {
    this.visible = visible
    this.fpsInterval = 1000 / (visible ? FPS_VISIBLE : FPS_HIDDEN)
    this.lastFrameTime = 0
  }

  /** 响应窗口大小变化 */
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

  /** 获取 canvas 元素（用于截图） */
  getCanvas(): HTMLCanvasElement | null {
    return this.renderer?.domElement ?? null
  }

  /**
   * 获取截图 base64（同步，Electron 同进程无跨域问题）
   * 比 toBlob→readAsDataURL 链路更短
   */
  getScreenshotDataURL(): string | null {
    const canvas = this.renderer?.domElement
    if (!canvas) return null
    try {
      return canvas.toDataURL('image/png')
    } catch {
      return null
    }
  }

  // ── 鼠标追踪 ──────────────────────────────────────

  /** 设置鼠标归一化坐标（由外部 IPC 调用） */
  setMousePosition(normalizedX: number, normalizedY: number): void {
    this.mouseX = normalizedX
    this.mouseY = normalizedY
  }

  /** 模型加载后查找头部/眼球骨骼并缓存引用 */
  private findHeadAndEyeBones(): void {
    this.headBone = null
    this.eyeBones = []
    this.eyeRestRotations = []

    if (!this.mesh) return

    this.mesh.traverse((child) => {
      if (!(child instanceof THREE.Bone)) return

      const name = child.name

      // 头部骨骼
      if (!this.headBone && HEAD_BONE_NAMES.some((n) => name.includes(n))) {
        this.headBone = child
        this.headRestRotation.copy(child.rotation)
      }

      // 眼球骨骼
      if (EYE_BONE_NAMES.some((n) => name.includes(n))) {
        this.eyeBones.push(child)
        this.eyeRestRotations.push(child.rotation.clone())
      }
    })
  }

  /** 每帧更新头部/眼球朝向鼠标方向（平滑插值） */
  private updateMouseLook(): void {
    if (!this.mesh || (!this.headBone && this.eyeBones.length === 0)) return

    // 鼠标坐标转为旋转角度（弧度）
    // mouseX: -1(左) ~ 1(右) → 水平旋转 ±25°
    // mouseY: -1(上) ~ 1(下) → 垂直旋转 ±15°
    const targetYaw = this.mouseX * 0.44   // ~25°
    const targetPitch = -this.mouseY * 0.26 // ~15°（Y 轴反转）

    // 头部跟随（全角度）
    if (this.headBone) {
      this.headBone.rotation.y = THREE.MathUtils.lerp(
        this.headBone.rotation.y,
        this.headRestRotation.y + targetYaw,
        MOUSE_LERP,
      )
      this.headBone.rotation.x = THREE.MathUtils.lerp(
        this.headBone.rotation.x,
        this.headRestRotation.x + targetPitch,
        MOUSE_LERP,
      )
    }

    // 眼球跟随（较小角度，更加灵敏）
    const eyeYaw = targetYaw * 0.6
    const eyePitch = targetPitch * 0.6
    for (let i = 0; i < this.eyeBones.length; i++) {
      const bone = this.eyeBones[i]
      const rest = this.eyeRestRotations[i]
      if (!bone || !rest) continue
      bone.rotation.y = THREE.MathUtils.lerp(
        bone.rotation.y,
        rest.y + eyeYaw,
        MOUSE_LERP * 1.5,
      )
      bone.rotation.x = THREE.MathUtils.lerp(
        bone.rotation.x,
        rest.x + eyePitch,
        MOUSE_LERP * 1.5,
      )
    }
  }

  private handleResize = (): void => {
    this.resize()
  }

  private setupContextLossHandlers(): void {
    if (!this.renderer) return

    const canvas = this.renderer.domElement

    this.contextLostHandler = (event: Event): void => {
      event.preventDefault()
      console.warn('[PetScene] WebGL context lost, pausing render')
      this.contextLost = true
    }

    this.contextRestoredHandler = (): void => {
      console.log('[PetScene] WebGL context restored, resuming render')
      this.contextLost = false
      this.lastFrameTime = 0
    }

    canvas.addEventListener('webglcontextlost', this.contextLostHandler)
    canvas.addEventListener('webglcontextrestored', this.contextRestoredHandler)
  }

  private removeContextLossHandlers(): void {
    if (!this.renderer) return
    const canvas = this.renderer.domElement
    if (this.contextLostHandler) {
      canvas.removeEventListener('webglcontextlost', this.contextLostHandler)
      this.contextLostHandler = null
    }
    if (this.contextRestoredHandler) {
      canvas.removeEventListener('webglcontextrestored', this.contextRestoredHandler)
      this.contextRestoredHandler = null
    }
  }

  /** 销毁资源 */
  dispose(): void {
    window.removeEventListener('resize', this.handleResize)

    this.removeContextLossHandlers()

    if (this.animationId !== null) {
      cancelAnimationFrame(this.animationId)
      this.animationId = null
    }

    if (this.mesh) {
      this.scene?.remove(this.mesh)
      this.mesh.geometry.dispose()
      if (Array.isArray(this.mesh.material)) {
        this.mesh.material.forEach((m) => m.dispose())
      } else if (this.mesh.material instanceof THREE.Material) {
        this.mesh.material.dispose()
      }
    }

    this.controls?.dispose()
    this.controls = null

    this.helper?.dispose()

    this.renderer?.dispose()
    this.renderer?.domElement.remove()

    this.renderer = null
    this.scene = null
    this.camera = null
    this.clock = null
    this.mesh = null
    this.helper = null
    this.loader = null
    this._isLoaded = false
  }
}
