import * as THREE from 'three'

/** 加载超时时间 (ms) */
const LOAD_TIMEOUT_MS = 10_000
/** 可见时帧率 */
const FPS_VISIBLE = 60
/** 不可见时帧率 */
const FPS_HIDDEN = 5

/**
 * 宠物 3D 场景管理
 * 负责：Three.js 场景初始化、PMX 模型加载、VMD 动画、渲染循环、截图
 *
 * 使用 Three.js r171 官方 MMDLoader（本地模块）
 */
export class PetScene {
  private container: HTMLElement
  private renderer: THREE.WebGLRenderer | null = null
  private scene: THREE.Scene | null = null
  private camera: THREE.PerspectiveCamera | null = null
  private clock: THREE.Clock | null = null
  private animationId: number | null = null
  private visible = true
  private mesh: THREE.SkinnedMesh | null = null
  private helper: any = null
  private loader: any = null

  /** 帧率控制 */
  private lastFrameTime = 0
  private fpsInterval = 1000 / FPS_VISIBLE

  /** 模型是否已成功加载 */
  private _isLoaded = false

  /** WebGL context 丢失标记 */
  private contextLost = false
  private contextLostHandler: (() => void) | null = null
  private contextRestoredHandler: (() => void) | null = null

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
    this.container.appendChild(this.renderer.domElement)

    // WebGL context 丢失/恢复处理
    this.setupContextLossHandlers()

    // 场景
    this.scene = new THREE.Scene()

    // 相机
    this.camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000)
    this.camera.position.set(0, 12, 25)
    this.camera.lookAt(0, 10, 0)

    // 灯光
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6)
    this.scene.add(ambientLight)

    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8)
    directionalLight.position.set(5, 10, 7)
    this.scene.add(directionalLight)

    const backLight = new THREE.DirectionalLight(0xffffff, 0.3)
    backLight.position.set(-5, 5, -5)
    this.scene.add(backLight)

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
  async loadModel(modelPath: string): Promise<void> {
    if (!this.scene) throw new Error('Scene not initialized')
    if (!this.loader) {
      console.warn('[PetScene] loadModel skipped: MMDLoader not available')
      return
    }

    return new Promise((resolve, reject) => {
      const timeoutId = setTimeout(() => {
        reject(new Error(`模型加载超时 (${LOAD_TIMEOUT_MS / 1000}s): ${modelPath}`))
      }, LOAD_TIMEOUT_MS)

      this.loader!.load(
        modelPath,
        (mesh) => {
          clearTimeout(timeoutId)
          this.replaceMesh(mesh)
          this.scene!.add(mesh)
          this.fitCameraToModel(mesh)
          this._isLoaded = true
          resolve()
        },
        undefined,
        (error) => {
          clearTimeout(timeoutId)
          reject(error instanceof Error ? error : new Error(String(error)))
        }
      )
    })
  }

  /** 加载 PMX 模型 + VMD 动画（官方 loadWithAnimation），超时 10s */
  async loadModelWithAnimation(
    modelPath: string,
    vmdPath: string
  ): Promise<void> {
    if (!this.scene) throw new Error('Scene not initialized')
    if (!this.loader) {
      console.warn('[PetScene] loadModelWithAnimation skipped: MMDLoader not available')
      return
    }

    return new Promise((resolve, reject) => {
      const timeoutId = setTimeout(() => {
        reject(new Error(`模型+动画加载超时 (${LOAD_TIMEOUT_MS / 1000}s): ${modelPath}`))
      }, LOAD_TIMEOUT_MS)

      this.loader!.loadWithAnimation(
        modelPath,
        vmdPath,
        (result) => {
          clearTimeout(timeoutId)

          const { mesh, animation } = result

          this.replaceMesh(mesh)

          // 通过 MMDAnimationHelper 管理动画 + IK + 物理（如果 helper 可用）
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
          resolve()
        },
        undefined,
        (error) => {
          clearTimeout(timeoutId)
          reject(error instanceof Error ? error : new Error(String(error)))
        }
      )
    })
  }

  /** 替换旧模型 */
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
    this._isLoaded = false
    this.mesh = mesh
  }

  /** 自动调整相机以适配模型 */
  private fitCameraToModel(mesh: THREE.SkinnedMesh): void {
    if (!this.camera) return

    const box = new THREE.Box3().setFromObject(mesh)
    const center = box.getCenter(new THREE.Vector3())
    const size = box.getSize(new THREE.Vector3())
    const maxDim = Math.max(size.x, size.y, size.z, 0.1) // 防止除零
    const fov = this.camera.fov * (Math.PI / 180)
    const distance = Math.max(maxDim / (2 * Math.tan(fov / 2)), 5) // 最小距离 5

    this.camera.position.set(center.x, center.y, center.z + distance * 1.5)
    this.camera.lookAt(center)
  }

  /** 渲染循环（基于时间戳的帧率控制） */
  private startRenderLoop(): void {
    const animate = (timestamp: number): void => {
      this.animationId = requestAnimationFrame(animate)

      // 帧率节流
      const elapsed = timestamp - this.lastFrameTime
      if (elapsed < this.fpsInterval) return
      this.lastFrameTime = timestamp

      // context 丢失时跳过渲染
      if (this.contextLost) return

      if (!this.renderer || !this.scene || !this.camera) return

      const delta = this.clock!.getDelta()

      // 更新 MMD 动画（IK、物理、morph 都由 helper 统一处理）
      if (this.helper) {
        try {
          this.helper.update(delta)
        } catch {
          // helper 更新失败时静默忽略（例如模型被移除后残留的 helper 引用）
        }
      }

      // 检查 context 状态后再渲染
      try {
        this.renderer.render(this.scene, this.camera)
      } catch {
        // 渲染失败时静默忽略（context 恢复中可能会出现）
      }
    }

    // 用 0 时间戳启动，这样第一帧一定会渲染
    this.animationId = requestAnimationFrame(animate)
  }

  /** 设置可见性（控制帧率节省资源） */
  setVisible(visible: boolean): void {
    this.visible = visible
    this.fpsInterval = 1000 / (visible ? FPS_VISIBLE : FPS_HIDDEN)
    // 立即重置 lastFrameTime，切换后尽快渲染一帧
    this.lastFrameTime = 0
  }

  /** 响应窗口大小变化（公开方法，外部可调用） */
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

  /** 窗口大小变化处理器（内部 resize 事件绑定用） */
  private handleResize = (): void => {
    this.resize()
  }

  /** WebGL context 丢失处理 */
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

  /** 清理 WebGL context 事件监听器 */
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
