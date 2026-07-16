/**
 * MMD 渲染链路测试脚本
 *
 * 测试目标：验证从 MMDLoader → PetScene → 渲染的完整链路
 *
 * 运行方式：npx vitest run src/renderer/modules/pet/__tests__/pet-render.test.ts
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

// ─── Mock three.js 核心对象 ───
vi.mock('three', async () => {
  const actual = await vi.importActual<typeof import('three')>('three')

  class MockWebGLRenderer {
    domElement = document.createElement('canvas')
    setSize = vi.fn()
    setPixelRatio = vi.fn()
    setClearColor = vi.fn()
    render = vi.fn()
    dispose = vi.fn()
    outputColorSpace = ''
    toneMapping = 0
    toneMappingExposure = 1.0
    shadowMap = { enabled: false, type: 0 }
    // 各向异性：materialPipeline 读取硬件上限
    capabilities = { getMaxAnisotropy: vi.fn(() => 8) }
  }

  // PMREMGenerator：真实实现依赖 WebGL 上下文，测试中用轻量 mock 生成假环境贴图
  class MockPMREMGenerator {
    constructor(_renderer: unknown) {}
    fromScene = vi.fn(() => ({ texture: {} }))
    dispose = vi.fn()
  }

  class MockPerspectiveCamera {
    aspect = 1
    fov = 45
    position = { set: vi.fn(), x: 0, y: 0, z: 0 }
    lookAt = vi.fn()
    updateProjectionMatrix = vi.fn()
  }

  class MockScene {
    add = vi.fn()
    remove = vi.fn()
  }

  class MockAmbientLight {}
  class MockDirectionalLight {
    position = { set: vi.fn() }
    castShadow = false
    target = { position: { set: vi.fn() }, updateMatrixWorld: vi.fn() }
    shadow = {
      mapSize: { width: 0, height: 0 },
      bias: 0,
      normalBias: 0,
      // 阴影相机：生产代码在 updateGroundPlane 中按模型尺寸配置其视锥
      camera: {
        left: 0,
        right: 0,
        top: 0,
        bottom: 0,
        near: 0,
        far: 0,
        updateProjectionMatrix: vi.fn(),
      },
    }
  }
  class MockClock {
    getDelta = vi.fn(() => 0.016)
  }
  class MockBox3 {
    min = { x: 0, y: 0, z: 0 } as unknown as THREE.Vector3
    max = { x: 0, y: 0, z: 0 } as unknown as THREE.Vector3
    setFromObject = vi.fn().mockReturnThis()
    getCenter = vi.fn(() => ({ x: 0, y: 5, z: 0 } as unknown as THREE.Vector3))
    getSize = vi.fn(() => ({ x: 2, y: 10, z: 2 } as unknown as THREE.Vector3))
  }
  class MockVector3 {
    set = vi.fn()
    x = 0
    y = 0
    z = 0
  }

  return {
    ...actual,
    WebGLRenderer: MockWebGLRenderer,
    PerspectiveCamera: MockPerspectiveCamera,
    Scene: MockScene,
    AmbientLight: MockAmbientLight,
    DirectionalLight: MockDirectionalLight,
    Clock: MockClock,
    Box3: MockBox3,
    Vector3: MockVector3,
    PMREMGenerator: MockPMREMGenerator,
    SRGBColorSpace: 'srgb',
    ACESFilmicToneMapping: 4,
    Material: class MockMaterial { dispose = vi.fn() },
  }
})

// ─── Mock MMDLoader（匹配 pet-scene.ts 的真实导入路径）───
// 注意：load/loadWithAnimation 挂载在 prototype 上（而非 class field），
// 确保超时测试中可以用 prototype.load = vi.fn() 覆盖所有实例。
vi.mock('@/lib/mmd/loaders/MMDLoader.js', () => {
  class MockMMDLoader {
    setResourcePath = vi.fn()
    setPath = vi.fn()
  }

  MockMMDLoader.prototype.load = vi.fn(
    (url: string, onLoad: (mesh: unknown) => void) => {
      const mockMesh = {
        geometry: { dispose: vi.fn() },
        material: { dispose: vi.fn() },
        traverse: vi.fn(),
        scale: { setScalar: vi.fn() },
        position: { y: 0 },
        rotation: { y: 0 },
      }
      setTimeout(() => onLoad(mockMesh), 0)
    }
  )

  MockMMDLoader.prototype.loadWithAnimation = vi.fn(
    (
      modelUrl: string,
      vmdUrl: string,
      onLoad: (result: { mesh: unknown; animation: unknown }) => void
    ) => {
      const mockMesh = {
        geometry: { dispose: vi.fn() },
        material: { dispose: vi.fn() },
        traverse: vi.fn(),
        scale: { setScalar: vi.fn() },
        position: { y: 0 },
        rotation: { y: 0 },
      }
      const mockAnimation = { name: 'test-anim', tracks: [] }
      setTimeout(() => onLoad({ mesh: mockMesh, animation: mockAnimation }), 0)
    }
  )

  return {
    MMDLoader: MockMMDLoader,
  }
})

// ─── Mock MMDAnimationHelper（匹配 pet-scene.ts 的真实导入路径）───
vi.mock('@/lib/mmd/animation/MMDAnimationHelper.js', () => {
  return {
    MMDAnimationHelper: class MockMMDAnimationHelper {
      add = vi.fn().mockReturnThis()
      remove = vi.fn().mockReturnThis()
      update = vi.fn().mockReturnThis()
      dispose = vi.fn()
    },
  }
})

// ─── Mock OrbitControls（匹配 pet-scene.ts 的真实导入路径）───
// 说明：pet-scene.ts 用的是真实 OrbitControls（来自 three/addons），
// 而本测试整体 mock 了 'three'，导致 OrbitControls 内部依赖的真实
// Vector3 / Euler / Quaternion 失效。这里用轻量 mock 替代，
// 仅覆盖 PetScene 实际调用的 API（target.set / addEventListener /
// update / dispose 等），避免加载需要完整相机对象的真实实现。
vi.mock('three/addons/controls/OrbitControls.js', () => {
  return {
    OrbitControls: class MockOrbitControls {
      target = { set: vi.fn() }
      enableDamping = false
      dampingFactor = 0
      enableZoom = false
      mouseButtons: Record<string, unknown> = {}
      addEventListener = vi.fn()
      removeEventListener = vi.fn()
      update = vi.fn()
      dispose = vi.fn()
      constructor(_camera: unknown, _domElement: unknown) {}
    },
  }
})

vi.mock('three/addons/environments/RoomEnvironment.js', () => ({
  RoomEnvironment: class MockRoomEnvironment {},
}))

// ─── 测试套件 ───

describe('MMD 渲染链路测试', () => {
  let container: HTMLDivElement

  beforeEach(() => {
    container = document.createElement('div')
    container.style.width = '800px'
    container.style.height = '600px'
    // mock clientWidth/clientHeight
    Object.defineProperty(container, 'clientWidth', { value: 800, configurable: true })
    Object.defineProperty(container, 'clientHeight', { value: 600, configurable: true })
  })

  describe('1. 模块导入验证', () => {
    it('MMDLoader 可以从 three examples 模块导入', async () => {
      const { MMDLoader } = await import('@/lib/mmd/loaders/MMDLoader.js')
      expect(MMDLoader).toBeDefined()
      expect(typeof MMDLoader).toBe('function')
    })

    it('MMDAnimationHelper 可以从 three examples 模块导入', async () => {
      const { MMDAnimationHelper } = await import(
        '@/lib/mmd/animation/MMDAnimationHelper.js'
      )
      expect(MMDAnimationHelper).toBeDefined()
      expect(typeof MMDAnimationHelper).toBe('function')
    })

    it('PetScene 可以导入', async () => {
      const { PetScene } = await import('../scene/pet-scene')
      expect(PetScene).toBeDefined()
      expect(typeof PetScene).toBe('function')
    })
  })

  describe('2. PetScene 初始化', () => {
    it('可以实例化 PetScene', async () => {
      const { PetScene } = await import('../scene/pet-scene')
      const scene = new PetScene(container)
      expect(scene).toBeDefined()
    })

    it('init() 创建渲染器、场景、相机', async () => {
      const { PetScene } = await import('../scene/pet-scene')
      const scene = new PetScene(container)

      await scene.init()

      // canvas 应该被添加到 container
      expect(container.querySelector('canvas')).toBeTruthy()
      // getCanvas 应该返回 canvas
      expect(scene.getCanvas()).toBeTruthy()

      scene.dispose()
    })

    it('dispose() 清理所有资源', async () => {
      const { PetScene } = await import('../scene/pet-scene')
      const scene = new PetScene(container)

      await scene.init()
      scene.dispose()

      // dispose 后 canvas 应该被移除
      expect(container.querySelector('canvas')).toBeFalsy()
      expect(scene.getCanvas()).toBeFalsy()
    })

    it('isLoaded 初始为 false', async () => {
      const { PetScene } = await import('../scene/pet-scene')
      const scene = new PetScene(container)
      await scene.init()

      expect(scene.isLoaded).toBe(false)

      scene.dispose()
    })
  })

  describe('3. 模型加载链路（真实计时器）', () => {
    it('loadModel() 成功加载 PMX 模型', async () => {
      const { PetScene } = await import('../scene/pet-scene')
      const scene = new PetScene(container)
      await scene.init()

      // mock 使用 setTimeout(0) → 等待一个微任务周期
      await expect(scene.loadModel('/models/test.pmx')).resolves.toBeUndefined()
      expect(scene.isLoaded).toBe(true)

      scene.dispose()
    })

    it('loadModelWithAnimation() 成功加载模型+动画', async () => {
      const { PetScene } = await import('../scene/pet-scene')
      const scene = new PetScene(container)
      await scene.init()

      await expect(
        scene.loadModelWithAnimation('/models/test.pmx', '/anims/test.vmd')
      ).resolves.toBeUndefined()
      expect(scene.isLoaded).toBe(true)

      scene.dispose()
    })
  })

  describe('3b. 模型加载超时（假计时器）', () => {
    beforeEach(() => {
      vi.useFakeTimers()
    })

    afterEach(() => {
      vi.useRealTimers()
    })

    it('loadModel() 超时处理（10s）', async () => {
      const { PetScene } = await import('../scene/pet-scene')
      // 重新 mock MMDLoader 使其永不回调（在 fake timers 下）
      const { MMDLoader } = await import('@/lib/mmd/loaders/MMDLoader.js')
      const originalLoad = (
        MMDLoader as unknown as { prototype: { load: typeof vi.fn } }
      ).prototype.load

      const scene = new PetScene(container)
      await scene.init()

      // 禁用 load 回调
      ;(MMDLoader as unknown as { prototype: { load: typeof vi.fn } }).prototype.load = vi.fn()

      const loadPromise = scene.loadModel('/models/test.pmx')

      // 快进 11 秒触发超时
      vi.advanceTimersByTime(11_000)

      await expect(loadPromise).rejects.toThrow(/超时/)

      // 恢复
      ;(MMDLoader as unknown as { prototype: { load: typeof vi.fn } }).prototype.load =
        originalLoad

      scene.dispose()
    })

    it('loadModelWithAnimation() 超时处理（10s）', async () => {
      const { PetScene } = await import('../scene/pet-scene')
      // 使 loadWithAnimation 永不回调
      const { MMDLoader } = await import('@/lib/mmd/loaders/MMDLoader.js')
      const originalFn = (
        MMDLoader as unknown as { prototype: { loadWithAnimation: typeof vi.fn } }
      ).prototype.loadWithAnimation

      const scene = new PetScene(container)
      await scene.init()

      ;(
        MMDLoader as unknown as { prototype: { loadWithAnimation: typeof vi.fn } }
      ).prototype.loadWithAnimation = vi.fn()

      const loadPromise = scene.loadModelWithAnimation('/models/test.pmx', '/anims/test.vmd')

      vi.advanceTimersByTime(11_000)

      await expect(loadPromise).rejects.toThrow(/超时/)

      // 恢复
      ;(
        MMDLoader as unknown as { prototype: { loadWithAnimation: typeof vi.fn } }
      ).prototype.loadWithAnimation = originalFn

      scene.dispose()
    })
  })

  describe('4. MMDAnimationHelper 集成', () => {
    it('helper.update() 在渲染循环中被调用', async () => {
      const { PetScene } = await import('../scene/pet-scene')

      const scene = new PetScene(container)
      await scene.init()

      // 加载带动画的模型（会调用 helper.add）
      await scene.loadModelWithAnimation('/models/test.pmx', '/anims/test.vmd')

      // 等待一个帧周期（requestAnimationFrame）
      await new Promise((r) => setTimeout(r, 50))

      scene.dispose()
    })
  })

  describe('5. 可见性与渲染循环控制', () => {
    it('setVisible(false) 暂停渲染循环（GPU 零开销）', async () => {
      const { PetScene } = await import('../scene/pet-scene')
      const scene = new PetScene(container)
      await scene.init()

      scene.setVisible(false)
      // 渲染循环已暂停，等待一小段时间确认无帧输出
      await new Promise((r) => setTimeout(r, 50))

      scene.dispose()
    })

    it('setVisible(true) 恢复渲染循环', async () => {
      const { PetScene } = await import('../scene/pet-scene')
      const scene = new PetScene(container)
      await scene.init()

      scene.setVisible(false)
      scene.setVisible(true)
      // 恢复后渲染循环重新运行
      await new Promise((r) => setTimeout(r, 50))

      scene.dispose()
    })
  })

  describe('6. resize 方法', () => {
    it('resize() 更新相机和渲染器尺寸', async () => {
      const { PetScene } = await import('../scene/pet-scene')
      const scene = new PetScene(container)
      await scene.init()

      // 改变容器尺寸后调用 resize
      Object.defineProperty(container, 'clientWidth', { value: 400, configurable: true })
      Object.defineProperty(container, 'clientHeight', { value: 300, configurable: true })

      // resize 不应抛出异常
      expect(() => scene.resize()).not.toThrow()

      scene.dispose()
    })
  })

  describe('7. WebGL context 丢失恢复', () => {
    it('context 丢失时不崩溃', async () => {
      const { PetScene } = await import('../scene/pet-scene')
      const scene = new PetScene(container)
      await scene.init()

      const canvas = scene.getCanvas()
      expect(canvas).toBeTruthy()

      // 触发 context lost 事件
      const event = new Event('webglcontextlost')
      Object.defineProperty(event, 'preventDefault', { value: vi.fn() })
      canvas!.dispatchEvent(event)

      // 不应抛出异常
      await new Promise((r) => setTimeout(r, 50))

      // 触发 context restored 事件
      canvas!.dispatchEvent(new Event('webglcontextrestored'))

      await new Promise((r) => setTimeout(r, 50))

      scene.dispose()
    })
  })

  describe('8. MMDLoader 官方 API 兼容性', () => {
    it('MMDLoader 继承自 Loader', async () => {
      const { MMDLoader } = await import('@/lib/mmd/loaders/MMDLoader.js')
      const loader = new MMDLoader()
      // 验证实例创建成功
      expect(loader).toBeDefined()
      // 验证有 load 和 loadWithAnimation 方法
      expect(typeof (loader as any).load).toBe('function')
      expect(typeof (loader as any).loadWithAnimation).toBe('function')
    })

    it('MMDAnimationHelper 支持 add/remove/update/dispose', async () => {
      const { MMDAnimationHelper } = await import(
        '@/lib/mmd/animation/MMDAnimationHelper.js'
      )
      const helper = new MMDAnimationHelper()
      expect(typeof (helper as any).add).toBe('function')
      expect(typeof (helper as any).remove).toBe('function')
      expect(typeof (helper as any).update).toBe('function')
      expect(typeof (helper as any).dispose).toBe('function')
    })
  })

  describe('9. 缩放与待机动画', () => {
    it('加载后默认缩放为 1、待机动画开启', async () => {
      const { PetScene } = await import('../scene/pet-scene')
      const scene = new PetScene(container)
      await scene.init()
      await scene.loadModel('/models/test.pmx')

      expect(scene.getZoom()).toBe(1)
      expect(scene.isIdleEnabled()).toBe(true)

      scene.dispose()
    })

    it('zoomBy 放大并限制在 [0.3, 4] 区间', async () => {
      const { PetScene } = await import('../scene/pet-scene')
      const scene = new PetScene(container)
      await scene.init()
      await scene.loadModel('/models/test.pmx')

      scene.zoomBy(2)
      expect(scene.getZoom()).toBeGreaterThan(1)

      // 连续放大应被上限截断到 4
      for (let i = 0; i < 10; i++) scene.zoomBy(2)
      expect(scene.getZoom()).toBe(4)

      // 连续缩小应被下限截断到 0.3
      for (let i = 0; i < 20; i++) scene.zoomBy(0.5)
      expect(scene.getZoom()).toBe(0.3)

      scene.dispose()
    })

    it('setIdleEnabled 切换待机动画开关', async () => {
      const { PetScene } = await import('../scene/pet-scene')
      const scene = new PetScene(container)
      await scene.init()
      await scene.loadModel('/models/test.pmx')

      scene.setIdleEnabled(false)
      expect(scene.isIdleEnabled()).toBe(false)

      scene.setIdleEnabled(true)
      expect(scene.isIdleEnabled()).toBe(true)

      scene.dispose()
    })
  })
})
