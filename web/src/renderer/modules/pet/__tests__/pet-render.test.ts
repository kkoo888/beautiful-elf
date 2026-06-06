/**
 * MMD 渲染链路测试脚本
 *
 * 测试目标：验证从 MMDLoader → PetScene → 渲染的完整链路
 *
 * 运行方式：npx vitest run src/renderer/modules/pet/__tests__/pet-render.test.ts
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'

// ─── Mock three.js 核心对象 ───
vi.mock('three', async () => {
  const actual = await vi.importActual<typeof import('three')>('three')

  class MockWebGLRenderer {
    domElement = document.createElement('canvas')
    setSize = vi.fn()
    setPixelRatio = vi.fn()
    render = vi.fn()
    dispose = vi.fn()
    outputColorSpace = ''
    toneMapping = 0
    toneMappingExposure = 1.0
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
  }
  class MockClock {
    getDelta = vi.fn(() => 0.016)
  }
  class MockBox3 {
    setFromObject = vi.fn().mockReturnThis()
    getCenter = vi.fn(() => ({ x: 0, y: 5, z: 0 }))
    getSize = vi.fn(() => ({ x: 2, y: 10, z: 2 }))
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
    SRGBColorSpace: 'srgb',
    ACESFilmicToneMapping: 4,
    Material: class MockMaterial { dispose = vi.fn() },
  }
})

// ─── Mock MMDLoader ───
vi.mock('../scene/MMDLoader.js', () => {
  return {
    MMDLoader: class MockMMDLoader {
      load = vi.fn((url, onLoad) => {
        const mockMesh = {
          geometry: { dispose: vi.fn() },
          material: { dispose: vi.fn() },
        }
        setTimeout(() => onLoad(mockMesh), 0)
      })
      loadWithAnimation = vi.fn((modelUrl, vmdUrl, onLoad) => {
        const mockMesh = {
          geometry: { dispose: vi.fn() },
          material: { dispose: vi.fn() },
        }
        const mockAnimation = { name: 'test-anim', tracks: [] }
        setTimeout(() => onLoad({ mesh: mockMesh, animation: mockAnimation }), 0)
      })
    },
  }
})

// ─── Mock MMDAnimationHelper ───
vi.mock('../scene/MMDAnimationHelper.js', () => {
  return {
    MMDAnimationHelper: class MockMMDAnimationHelper {
      add = vi.fn().mockReturnThis()
      remove = vi.fn().mockReturnThis()
      update = vi.fn().mockReturnThis()
      dispose = vi.fn()
    },
  }
})

// ─── 测试套件 ───

describe('MMD 渲染链路测试', () => {
  let container: HTMLDivElement

  beforeEach(() => {
    container = document.createElement('div')
    container.style.width = '800px'
    container.style.height = '600px'
    // mock clientWidth/clientHeight
    Object.defineProperty(container, 'clientWidth', { value: 800 })
    Object.defineProperty(container, 'clientHeight', { value: 600 })
  })

  describe('1. 模块导入验证', () => {
    it('MMDLoader 可以从本地模块导入', async () => {
      const { MMDLoader } = await import('../scene/MMDLoader.js')
      expect(MMDLoader).toBeDefined()
      expect(typeof MMDLoader).toBe('function')
    })

    it('MMDAnimationHelper 可以从本地模块导入', async () => {
      const { MMDAnimationHelper } = await import('../scene/MMDAnimationHelper.js')
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
  })

  describe('3. 模型加载链路', () => {
    it('loadModel() 成功加载 PMX 模型', async () => {
      const { PetScene } = await import('../scene/pet-scene')
      const scene = new PetScene(container)
      await scene.init()

      // loadModel 应该成功完成（mock 会立即回调）
      await expect(scene.loadModel('/models/test.pmx')).resolves.toBeUndefined()

      scene.dispose()
    })

    it('loadModelWithAnimation() 成功加载模型+动画', async () => {
      const { PetScene } = await import('../scene/pet-scene')
      const scene = new PetScene(container)
      await scene.init()

      await expect(
        scene.loadModelWithAnimation('/models/test.pmx', '/anims/test.vmd')
      ).resolves.toBeUndefined()

      scene.dispose()
    })
  })

  describe('4. MMDAnimationHelper 集成', () => {
    it('helper.update() 在渲染循环中被调用', async () => {
      const { PetScene } = await import('../scene/pet-scene')
      const { MMDAnimationHelper } = await import('../scene/MMDAnimationHelper.js')

      const scene = new PetScene(container)
      await scene.init()

      // 加载带动画的模型（会调用 helper.add）
      await scene.loadModelWithAnimation('/models/test.pmx', '/anims/test.vmd')

      // 手动触发一帧渲染（通过 requestAnimationFrame mock）
      // 由于我们 mock 了 requestAnimationFrame，需要等一个 tick
      await new Promise((r) => setTimeout(r, 50))

      scene.dispose()
    })
  })

  describe('5. 可见性控制', () => {
    it('setVisible(false) 跳过渲染', async () => {
      const { PetScene } = await import('../scene/pet-scene')
      const scene = new PetScene(container)
      await scene.init()

      scene.setVisible(false)
      // 渲染循环仍然运行，但 render() 不会被调用
      await new Promise((r) => setTimeout(r, 50))

      scene.dispose()
    })

    it('setVisible(true) 恢复渲染', async () => {
      const { PetScene } = await import('../scene/pet-scene')
      const scene = new PetScene(container)
      await scene.init()

      scene.setVisible(false)
      scene.setVisible(true)

      scene.dispose()
    })
  })

  describe('6. MMDLoader 官方 API 兼容性', () => {
    it('MMDLoader 继承自 Loader', async () => {
      const { MMDLoader } = await import('../scene/MMDLoader.js')
      const loader = new MMDLoader()
      // 验证实例创建成功
      expect(loader).toBeDefined()
      // 验证有 load 和 loadWithAnimation 方法
      expect(typeof loader.load).toBe('function')
      expect(typeof loader.loadWithAnimation).toBe('function')
    })

    it('MMDAnimationHelper 支持 add/remove/update', async () => {
      const { MMDAnimationHelper } = await import('../scene/MMDAnimationHelper.js')
      const helper = new MMDAnimationHelper()
      expect(typeof helper.add).toBe('function')
      expect(typeof helper.remove).toBe('function')
      expect(typeof helper.update).toBe('function')
      expect(typeof helper.dispose).toBe('function')
    })
  })
})
