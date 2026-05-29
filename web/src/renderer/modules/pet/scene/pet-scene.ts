import * as THREE from 'three'
import { MMDLoader } from 'three-mmd-loader'

/**
 * 宠物 3D 场景管理
 * 负责：Three.js 场景初始化、PMX 模型加载、渲染循环、截图
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

  constructor(container: HTMLElement) {
    this.container = container
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

    // 响应窗口大小变化
    window.addEventListener('resize', this.handleResize)

    // 开始渲染循环
    this.startRenderLoop()
  }

  /** 加载 PMX 模型 */
  async loadModel(modelPath: string): Promise<void> {
    if (!this.scene) throw new Error('Scene not initialized')

    const loader = new MMDLoader()

    return new Promise((resolve, reject) => {
      loader.load(
        modelPath,
        (mesh) => {
          // 移除旧模型
          if (this.mesh) {
            this.scene!.remove(this.mesh)
            this.mesh.geometry.dispose()
            if (this.mesh.material instanceof THREE.Material) {
              this.mesh.material.dispose()
            }
          }

          this.mesh = mesh
          this.scene!.add(mesh)
          this.fitCameraToModel(mesh)
          resolve()
        },
        undefined,
        (error) => {
          reject(error)
        }
      )
    })
  }

  /** 自动调整相机以适配模型 */
  private fitCameraToModel(mesh: THREE.SkinnedMesh): void {
    if (!this.camera) return

    const box = new THREE.Box3().setFromObject(mesh)
    const center = box.getCenter(new THREE.Vector3())
    const size = box.getSize(new THREE.Vector3())
    const maxDim = Math.max(size.x, size.y, size.z)
    const fov = this.camera.fov * (Math.PI / 180)
    const distance = maxDim / (2 * Math.tan(fov / 2))

    this.camera.position.set(center.x, center.y, center.z + distance * 1.5)
    this.camera.lookAt(center)
  }

  /** 渲染循环 */
  private startRenderLoop(): void {
    const animate = () => {
      this.animationId = requestAnimationFrame(animate)

      if (!this.visible) return // 不可见时跳过渲染

      const delta = this.clock!.getDelta()

      // 更新模型动画（如果有时钟/动画混合器）
      if (this.mesh && (this.mesh as any).geometry) {
        // MMD 动画更新由 MMDLoader 内部处理
      }

      this.renderer!.render(this.scene!, this.camera!)
    }

    animate()
  }

  /** 设置可见性（控制帧率节省资源） */
  setVisible(visible: boolean): void {
    this.visible = visible
  }

  /** 获取 canvas 元素（用于截图） */
  getCanvas(): HTMLCanvasElement | null {
    return this.renderer?.domElement ?? null
  }

  /** 窗口大小变化处理 */
  private handleResize = (): void => {
    const width = this.container.clientWidth
    const height = this.container.clientHeight

    if (this.camera) {
      this.camera.aspect = width / height
      this.camera.updateProjectionMatrix()
    }

    this.renderer?.setSize(width, height)
  }

  /** 销毁资源 */
  dispose(): void {
    window.removeEventListener('resize', this.handleResize)

    if (this.animationId !== null) {
      cancelAnimationFrame(this.animationId)
    }

    if (this.mesh) {
      this.scene?.remove(this.mesh)
      this.mesh.geometry.dispose()
      if (this.mesh.material instanceof THREE.Material) {
        this.mesh.material.dispose()
      }
    }

    this.renderer?.dispose()
    this.renderer?.domElement.remove()

    this.renderer = null
    this.scene = null
    this.camera = null
    this.clock = null
    this.mesh = null
  }
}
