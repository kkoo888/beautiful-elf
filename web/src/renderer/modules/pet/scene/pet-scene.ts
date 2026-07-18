import * as THREE from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js'

// ════════════════════════════════════════════════════════════
// 常量
// ════════════════════════════════════════════════════════════

const LOAD_TIMEOUT_BASE_MS = 10_000
const LOAD_TIMEOUT_PER_MB_MS = 2_000
const LOAD_MAX_RETRIES = 1
const FPS_VISIBLE = 60
const CAMERA_PADDING = 1.2
const MOUSE_LERP = 0.08
const MOUSE_CONVERGE_THRESHOLD = 0.001
const DELTA_CLAMP = 0.1 // 最大帧间隔 100ms，防止 tab 切换/resize 等异常跳帧
const SHADOW_MAP_SIZE = 512 // 桌面宠物 400x500 窗口，512 足够
const HEAD_BONE_NAMES = ['頭', 'head', 'Head', '頭部']
const EYE_BONE_NAMES = ['左目', '右目', 'leftEye', 'rightEye', 'Eye_L', 'Eye_R']

export type LoadProgressCallback = (progress: number, status: string) => void

// IBL 环境贴图缓存（RoomEnvironment 是固定内容，全生命周期复用一次）
let _cachedEnvTexture: THREE.Texture | null = null

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
  // MMDLoader 和 MMDAnimationHelper 通过动态 import 加载，类型在 setupLoaders 中赋值
  private loader: {
    load(url: string, onLoad: (mesh: THREE.SkinnedMesh) => void, onProgress?: (event: ProgressEvent) => void, onError?: (error: unknown) => void): void
    loadWithAnimation(url: string, vmdUrl: string, onLoad: (result: { mesh: THREE.SkinnedMesh; animation: THREE.AnimationClip }) => void, onProgress?: (event: ProgressEvent) => void, onError?: (error: unknown) => void): void
    setResourcePath(path: string): void
  } | null = null
  private helper: {
    add(mesh: THREE.SkinnedMesh, options: { animation: THREE.AnimationClip; physics: boolean }): void
    update(delta: number): void
    dispose(): void
  } | null = null
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
  private groundGeo: THREE.PlaneGeometry | null = null // 复用的地面几何体
  private groundMat: THREE.ShadowMaterial | null = null // 复用的地面材质
  private dirLight: THREE.DirectionalLight | null = null // 主定向光（投影阴影）
  private clock: THREE.Clock | null = null

  private _isLoaded = false

  // ── 缩放 / 待机动画（动作） ──
  private zoomScale = 1
  private idleEnabled = true
  private idleBaseY = 0
  /** 模型脚底在 scale=1 时的世界 Y，用于缩放时把脚底锚定到该高度，使宠物始终贴窗口底部 */
  private anchorFeetY = 0
  private elapsedTime = 0
  private static readonly ZOOM_MIN = 0.3
  private static readonly ZOOM_MAX = 4

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

  /** 检测是否支持 VSM 阴影（需要高精度浮点纹理 + 二次采样） */
  private _supportsVSM(): boolean {
    try {
      const gl = document.createElement('canvas').getContext('webgl2') || document.createElement('canvas').getContext('webgl')
      if (!gl) return false
      // VSM 需要浮点颜色缓冲；检查 OES_texture_float 或 WebGL2 内置支持
      const isWebGL2 = (gl as WebGL2RenderingContext).MAX_SAMPLES !== undefined
      if (isWebGL2) return true
      return !!gl.getExtension('OES_texture_float')
    } catch {
      return false
    }
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
    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, premultipliedAlpha: false, preserveDrawingBuffer: true })
    this.renderer.setSize(width, height)
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    this.renderer.outputColorSpace = THREE.SRGBColorSpace
    // AgX 色调映射：比 ACES 更中性、胶片底片感，是新场景更好的基线（three r161+）
    this.renderer.toneMapping = THREE.AgXToneMapping
    this.renderer.toneMappingExposure = 1.0
    this.renderer.shadowMap.enabled = true
    // 阴影类型自适应：高端 GPU 用 VSM 软阴影，低端降级为 PCFSoftShadowMap
    // VSM 需要额外 blur pass（~2x 开销），低端设备可能卡顿
    this.renderer.shadowMap.type = this._supportsVSM()
      ? THREE.VSMShadowMap
      : THREE.PCFSoftShadowMap
    // 保持窗口透明（clearColor alpha=0），供无边框桌宠窗口叠加桌面
    this.renderer.setClearColor(0x000000, 0)
    this.container.appendChild(this.renderer.domElement)
    this.setupContextLossHandlers()

    // 场景
    this.scene = new THREE.Scene()

    // IBL 环境光（RoomEnvironment 摄影棚）：为 PBR 材质提供基于图像的漫/镜反射，
    // 补上「只有直射+环境光」的扁平感。注意：MMDToonMaterial 是自定义 shader，
    // 默认不吃 scene.environment，此项主要惠及 materialPipeline 中转成 Standard 的部件。
    this.setupEnvironment()

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

    // 滚轮缩放（在宠物窗口内直接滚轮放大缩小）
    this.renderer.domElement.addEventListener('wheel', this.handleWheel)

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

  /** IBL 环境：RoomEnvironment 经 PMREM 生成环境贴图，缓存复用 */
  private setupEnvironment(): void {
    if (!this.renderer || !this.scene) return
    try {
      if (_cachedEnvTexture) {
        this.scene.environment = _cachedEnvTexture
        return
      }
      const pmrem = new THREE.PMREMGenerator(this.renderer)
      const envScene = new RoomEnvironment()
      _cachedEnvTexture = pmrem.fromScene(envScene, 0.04).texture
      this.scene.environment = _cachedEnvTexture
      pmrem.dispose()
    } catch (e) {
      console.warn('[PetScene] setupEnvironment failed:', e)
    }
  }

  /** 4 灯配置：环境光 + 半球光 + 主定向光（阴影）+ 补光 + 轮廓光 */
  private setupLights(): void {
    if (!this.scene) return

    // 环境光
    this.scene.add(new THREE.AmbientLight(0xffffff, 0.6))

    // 半球光（天空/地面渐变）
    this.scene.add(new THREE.HemisphereLight(0xddeeff, 0x202020, 0.5))

    // 主定向光 + 阴影（512 足够桌面宠物）
    // 注意：DirectionalLight 默认阴影正交视锥仅为 ±5 且 target 在原点，
    // 模型加载后需在 updateGroundPlane 中按模型尺寸重新配置阴影相机并瞄准模型中心，
    // 否则脚底阴影会被裁切/偏移。此处仅创建并保存引用。
    const dirLight = new THREE.DirectionalLight(0xffffff, 1.2)
    dirLight.position.set(20, 50, 30)
    dirLight.castShadow = true
    dirLight.shadow.mapSize.width = SHADOW_MAP_SIZE
    dirLight.shadow.mapSize.height = SHADOW_MAP_SIZE
    // 阴影参数：VSM 用 radius/blurSamples 控制柔和度，PCF 用 radius 控制采样范围
    dirLight.shadow.bias = 0
    dirLight.shadow.normalBias = 0.05
    if (this.renderer?.shadowMap.type === THREE.VSMShadowMap) {
      dirLight.shadow.radius = 3
      dirLight.shadow.blurSamples = 8
    } else {
      dirLight.shadow.radius = 2
    }
    this.dirLight = dirLight
    this.scene.add(dirLight)
    // target 必须加入场景图，其 matrixWorld 才会随模型加载后重新对准中心而更新
    this.scene.add(dirLight.target)

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

  /** 动态加载 MMDLoader + MMDAnimationHelper（从本地 lib/mmd/） */
  private async setupLoaders(): Promise<void> {
    try {
      // ammo.js 需要作为全局变量，MMDPhysics 依赖 window.Ammo
      await import('@mmd/libs/ammo.js')
    } catch (e) {
      console.warn('[PetScene] ammo.js load failed (physics disabled):', e)
    }

    try {
      const mod = await import('@mmd/loaders/MMDLoader.js')
      this.loader = new mod.MMDLoader()
    } catch (e) {
      console.warn('[PetScene] MMDLoader import failed:', e)
    }

    try {
      const mod = await import('@mmd/animation/MMDAnimationHelper.js')
      this.helper = new mod.MMDAnimationHelper({
        afterglow: 2.0,
        resetPhysicsOnLoop: true,
      })
    } catch (e) {
      console.warn('[PetScene] MMDAnimationHelper import failed:', e)
    }
  }

  /** 从模型路径中提取资源目录，确保纹理、toon 等相对资源能正确解析 */
  private getResourcePath(modelPath: string): string {
    const lastSlash = modelPath.lastIndexOf('/')
    return lastSlash >= 0 ? modelPath.substring(0, lastSlash + 1) : modelPath
  }

  /** 计算动态超时（大文件给更多时间） */
  private _calcTimeout(fileSize?: number): number {
    if (fileSize && fileSize > 0) {
      const mb = fileSize / (1024 * 1024)
      return Math.max(LOAD_TIMEOUT_BASE_MS, mb * LOAD_TIMEOUT_PER_MB_MS)
    }
    return LOAD_TIMEOUT_BASE_MS
  }

  /** 创建占位立方体（加载失败时的 fallback） */
  private _createPlaceholder(): THREE.Mesh {
    const geo = new THREE.BoxGeometry(2, 4, 2)
    const mat = new THREE.MeshStandardMaterial({ color: 0x888888, roughness: 0.7 })
    const cube = new THREE.Mesh(geo, mat)
    cube.castShadow = true
    cube.receiveShadow = true
    return cube
  }

  /** 加载 PMX 模型（无动画，支持重试 + fallback） */
  async loadModel(modelPath: string, onProgress?: LoadProgressCallback): Promise<void> {
    if (!this.scene || !this.loader) return
    onProgress?.(0, '加载模型中...')

    const modelDir = this.getResourcePath(modelPath)
    let lastError: Error | null = null

    for (let attempt = 0; attempt <= LOAD_MAX_RETRIES; attempt++) {
      try {
        if (attempt > 0) onProgress?.(0, `重试中 (${attempt}/${LOAD_MAX_RETRIES})...`)
        await this._loadModelOnce(modelPath, modelDir, onProgress)
        return // 成功
      } catch (e) {
        lastError = e instanceof Error ? e : new Error(String(e))
        if (attempt < LOAD_MAX_RETRIES) {
          await new Promise(r => setTimeout(r, 500)) // 重试前等 500ms
        }
      }
    }

    // 全部重试失败 → 显示占位立方体，不抛异常
    console.warn(`[PetScene] loadModel failed after ${LOAD_MAX_RETRIES + 1} attempts:`, lastError)
    this.disposeCurrentMesh()
    const placeholder = this._createPlaceholder()
    this.mesh = placeholder as unknown as THREE.SkinnedMesh
    this.scene.add(placeholder)
    this.fitCameraToModel(placeholder as unknown as THREE.SkinnedMesh)
    this._isLoaded = true
    onProgress?.(100, '加载失败，显示占位模型')
  }

  private _loadModelOnce(modelPath: string, modelDir: string, onProgress?: LoadProgressCallback): Promise<void> {
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => reject(new Error(`加载超时: ${modelPath}`)), this._calcTimeout())

      this.loader!.setResourcePath(modelDir)
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

  /** 加载 PMX 模型 + VMD 动画（支持重试） */
  async loadModelWithAnimation(
    modelPath: string,
    vmdPath: string,
    onProgress?: LoadProgressCallback,
  ): Promise<void> {
    if (!this.scene || !this.loader) return
    onProgress?.(0, '加载模型+动画中...')

    const modelDir = this.getResourcePath(modelPath)
    let lastError: Error | null = null

    for (let attempt = 0; attempt <= LOAD_MAX_RETRIES; attempt++) {
      try {
        if (attempt > 0) onProgress?.(0, `重试中 (${attempt}/${LOAD_MAX_RETRIES})...`)
        await this._loadModelWithAnimationOnce(modelPath, vmdPath, modelDir, onProgress)
        return
      } catch (e) {
        lastError = e instanceof Error ? e : new Error(String(e))
        if (attempt < LOAD_MAX_RETRIES) await new Promise(r => setTimeout(r, 500))
      }
    }

    console.warn(`[PetScene] loadModelWithAnimation failed after ${LOAD_MAX_RETRIES + 1} attempts:`, lastError)
    // 动画加载失败不 fallback，直接抛（动画是可选的）
    throw lastError
  }

  private _loadModelWithAnimationOnce(
    modelPath: string, vmdPath: string, modelDir: string, onProgress?: LoadProgressCallback,
  ): Promise<void> {
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => reject(new Error(`加载超时: ${modelPath}`)), this._calcTimeout())

      this.loader!.setResourcePath(modelDir)
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

    this.mesh = mesh

    // 重置缩放与待机动画基准（以模型当前位置为浮动基准）
    mesh.scale.setScalar(1)
    const box0 = new THREE.Box3().setFromObject(mesh)
    this.anchorFeetY = box0.min.y // 脚底世界 Y（scale=1 时），缩放时脚底锚定于此
    this.idleBaseY = mesh.position.y
    this.zoomScale = 1
    this.elapsedTime = 0

    // 4. 添加到场景
    this.scene!.add(mesh)

    // 5. 动态阴影地面（基于模型 bbox）
    this.updateGroundPlane(mesh)

    // 6. 相机适配
    this.fitCameraToModel(mesh)

    // 7. 骨骼缓存
    this.findHeadAndEyeBones()

    // 模型已成功应用至场景，标记加载完成
    this._isLoaded = true
  }

  /** 材质管线：保留 MMD toon / Standard / Toon / 通用回退 */
  private materialPipeline(mesh: THREE.SkinnedMesh): void {
    const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material]

    // 纹理各向异性：斜视/转头时贴图更锐利（取硬件上限）
    const maxAniso = this.renderer?.capabilities?.getMaxAnisotropy?.() ?? 1

    const result = materials.map((mat) => {
      // 纹理增强：对所有材质的漫反射贴图统一设各向异性 + sRGB 色彩空间
      const diffuse = ('map' in mat ? mat.map : null) as THREE.Texture | undefined | null
      if (diffuse) {
        diffuse.anisotropy = maxAniso
        diffuse.colorSpace = THREE.SRGBColorSpace
        diffuse.needsUpdate = true
      }

      // MMDLoader 输出的专用 toon shader 材质 —— 必须原样保留，不能替换成 PBR。
      // 否则 gradientMap / matcap / MMD 专用光照逻辑会全部丢失，模型变成黑色剪影。
      if ('isMMDToonMaterial' in mat && (mat as Record<string, unknown>).isMMDToonMaterial) {
        return mat
      }

      // 已经是 PBR/Standard → 直接用
      if (mat instanceof THREE.MeshStandardMaterial) {
        return mat
      }

      // 普通 Toon → 保留
      if (mat instanceof THREE.MeshToonMaterial) {
        mat.needsUpdate = true
        return mat
      }

      // 其他自定义 ShaderMaterial → 原样保留，避免破坏特殊 shader
      if (mat instanceof THREE.ShaderMaterial) {
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
        pbr.roughness = mat.shininess > 0 ? Math.max(0.2, 1.0 - mat.shininess / 100) : 0.6
        pbr.metalness = 0.1
        pbr.needsUpdate = true
        mat.dispose()
        return pbr
      }

      // 通用回退 → PBR
      const pbr = new THREE.MeshStandardMaterial()
      pbr.map = ('map' in mat ? mat.map : null) as THREE.Texture | null ?? null
      pbr.transparent = mat.transparent
      pbr.opacity = mat.opacity
      pbr.side = mat.side
      pbr.alphaTest = mat.alphaTest
      pbr.roughness = 0.5
      pbr.metalness = 0.1
      pbr.needsUpdate = true
      mat.dispose()
      return pbr
    })

    mesh.material = result.length === 1 ? result[0] : result
  }

  /** 动态阴影地面：根据模型 bbox 自动调整大小（复用几何体和材质） */
  private updateGroundPlane(mesh: THREE.SkinnedMesh): void {
    if (!this.scene) return

    // 移除旧地面（不 dispose 几何体和材质，后续复用）
    if (this.ground) {
      this.scene.remove(this.ground)
    }

    const box = new THREE.Box3().setFromObject(mesh)
    const size = box.getSize(new THREE.Vector3())
    const center = box.getCenter(new THREE.Vector3())
    const groundSize = Math.max(size.x, size.z) * CAMERA_PADDING * 3

    // 复用或创建几何体 + 材质
    if (!this.groundGeo) {
      this.groundGeo = new THREE.PlaneGeometry(groundSize, groundSize)
    } else {
      // PlaneGeometry 不支持直接 resize，用 scale 模拟
    }
    if (!this.groundMat) {
      this.groundMat = new THREE.ShadowMaterial({ opacity: 0.3 })
    }
    if (!this.ground) {
      this.ground = new THREE.Mesh(this.groundGeo, this.groundMat)
      this.ground.rotation.x = -Math.PI / 2
      this.ground.receiveShadow = true
    }
    // 用 scale 适配不同模型尺寸（基准 PlaneGeometry 是 1x1）
    this.ground.scale.set(groundSize, groundSize, 1)
    this.ground.position.y = box.min.y
    this.scene.add(this.ground)

    // 配置阴影相机覆盖整个模型，并将光源目标对准模型中心。
    // 否则 DirectionalLight 默认 ±5 的正交视锥太小、且默认 target 在原点，
    // 模型远大于该范围时脚底阴影会被裁切或偏移，无法完整落在地面。
    if (this.dirLight) {
      const cam = this.dirLight.shadow.camera
      const halfX = Math.max(size.x, size.z) * 1.5
      const halfY = size.y * 1.5
      cam.left = -halfX
      cam.right = halfX
      cam.top = halfY
      cam.bottom = -halfY
      cam.near = 0.1
      cam.far = 200
      cam.updateProjectionMatrix()
      this.dirLight.target.position.set(center.x, center.y, center.z)
      this.dirLight.target.updateMatrixWorld()
    }
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

    // 相机到模型平面（z=center.z）的实际距离，与下方 position.z 一致
    const camDist = distance * 1.5
    // 该平面上视口的半高（世界单位）：halfH = camDist * tan(fov/2)
    const halfH = camDist * Math.tan(fov / 2)

    // 脚底贴窗口底部：把相机注视点上移，使脚底落在视口底边附近
    // （留 BOTTOM_MARGIN 余量防止脚底被窗口底边裁切）。
    // 推导：视口底边世界 Y = targetY - halfH；令脚底 footY 落在底边上方
    // BOTTOM_MARGIN×(2halfH) 处 → footY = targetY - halfH + BOTTOM_MARGIN×2halfH
    // → targetY = footY + halfH×(1 - 2×BOTTOM_MARGIN)。
    // 配合渲染循环 anchorFeetY 锚定（缩放时脚底世界 Y 不变），
    // 缩放后脚底投影始终贴窗口底部，模型从脚底向上生长、不上浮。
    const BOTTOM_MARGIN = 0.04
    const footY = center.y - size.y / 2
    const targetY = footY + halfH * (1 - 2 * BOTTOM_MARGIN)

    this.camera.position.set(center.x, targetY, center.z + camDist)
    this.camera.lookAt(center.x, targetY, center.z)
    // 同步 OrbitControls 注视点，否则右键旋转时相机会跳回模型中心
    if (this.controls) {
      this.controls.target.set(center.x, targetY, center.z)
    }
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
      this.elapsedTime += delta

      // OrbitControls：只在交互中更新
      if (this.controlsActive) {
        this.controls?.update()
      }

      // 动画：有 VMD 动画时更新 helper（优先于待机动画）
      const vmdActive = !!(this.helper && this.hasAnimation)
      if (vmdActive) {
        try { this.helper.update(delta) } catch (e) { console.warn('[PetScene] helper.update failed:', e) }
      }

      // 网格变换：缩放（放大缩小）+ 待机动画（动作）
      if (this.mesh) {
        const idleActive = this.idleEnabled && !vmdActive
        const breath = idleActive ? 1 + Math.sin(this.elapsedTime * 2.2) * 0.02 : 1
        const s = this.zoomScale * breath
        this.mesh.scale.setScalar(s)
        // 锚定脚底到固定世界 Y（anchorFeetY）：缩放时模型从脚底向上生长，
        // 脚底始终贴在原位置（窗口底部），避免放大后整只宠物上浮。
        const floatOffset = idleActive ? Math.sin(this.elapsedTime * 1.6) * 0.2 * s : 0
        this.mesh.position.y =
          this.anchorFeetY - (this.anchorFeetY - this.idleBaseY) * s + floatOffset
        if (idleActive) {
          this.mesh.rotation.y = Math.sin(this.elapsedTime * 0.5) * 0.08
        } else {
          this.mesh.rotation.y = 0
        }
      }

      // 鼠标追踪：只在鼠标移动时更新
      if (this.mouseDirty) {
        this.updateMouseLook()
      }

      try { this.renderer.render(this.scene, this.camera) } catch (e) { console.warn('[PetScene] render failed:', e) }
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
    // MMD 头骨绕 +X 旋转为「低头」：鼠标在窗口顶部时 mouseY≈-1，需让宠物「抬头」，
    // 故 pitch = +mouseY（顶部→负值→抬头，底部→正值→低头），与视觉一致。
    const targetPitch = this.mouseY * 0.26

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

  /** 设置可见性：隐藏时暂停渲染循环，显示时恢复 */
  setVisible(visible: boolean): void {
    this.visible = visible
    if (visible) {
      this.fpsInterval = 1000 / FPS_VISIBLE
      this.lastFrameTime = 0
      // 恢复渲染循环
      if (this.animationId === null && !this.contextLost) {
        this.startRenderLoop()
      }
    } else {
      // 暂停渲染循环，释放 GPU
      if (this.animationId !== null) {
        cancelAnimationFrame(this.animationId)
        this.animationId = null
      }
    }
  }

  /** 滚轮缩放处理（宠物窗口内直接滚轮放大缩小） */
  private handleWheel = (e: WheelEvent): void => {
    e.preventDefault()
    this.zoomBy(e.deltaY < 0 ? 1.12 : 1 / 1.12)
  }

  /** 相对缩放（放大缩小），限制在 [ZOOM_MIN, ZOOM_MAX] */
  zoomBy(factor: number): void {
    this.zoomScale = Math.min(PetScene.ZOOM_MAX, Math.max(PetScene.ZOOM_MIN, this.zoomScale * factor))
  }

  /** 设置绝对缩放值 */
  setZoom(scale: number): void {
    this.zoomScale = Math.min(PetScene.ZOOM_MAX, Math.max(PetScene.ZOOM_MIN, scale))
  }

  /** 当前缩放值 */
  getZoom(): number {
    return this.zoomScale
  }

  /** 重置缩放到 1 */
  resetZoom(): void {
    this.zoomScale = 1
  }

  /** 开启/关闭待机动画（动作） */
  setIdleEnabled(enabled: boolean): void {
    this.idleEnabled = enabled
  }

  /** 待机动画是否开启 */
  isIdleEnabled(): boolean {
    return this.idleEnabled
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

  /** 异步截图 → Blob（用于 HTTP 上传） */
  getScreenshotBlob(callback: (blob: Blob | null) => void): void {
    const canvas = this.renderer?.domElement
    if (!canvas) { callback(null); return }
    try {
      canvas.toBlob((blob) => callback(blob), 'image/png')
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
    this.renderer?.domElement.removeEventListener('wheel', this.handleWheel)
    this.removeContextLossHandlers()

    if (this.animationId !== null) { cancelAnimationFrame(this.animationId); this.animationId = null }

    this.disposeCurrentMesh()

    if (this.ground) { this.scene?.remove(this.ground); this.ground = null }
    if (this.groundGeo) { this.groundGeo.dispose(); this.groundGeo = null }
    if (this.groundMat) { this.groundMat.dispose(); this.groundMat = null }

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
