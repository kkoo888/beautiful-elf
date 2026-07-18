/**
 * WorldApp — 虚拟世界 3D 渲染窗口
 *
 * 负责：
 *   1. 初始化 Three.js 场景 + 相机 + 灯光
 *   2. 从后端加载激活场景的方块数据
 *   3. 用 SceneBuilder (InstancedMesh) 渲染积木
 *   4. OrbitControls 交互
 *   5. 窗口可见性控制
 */
import { useEffect, useRef, useState, useCallback } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { Spin, Button } from 'antd'
import {
  LoadingOutlined,
  ZoomInOutlined,
  ZoomOutOutlined,
  ReloadOutlined,
  CloseOutlined,
} from '@ant-design/icons'
import { SceneBuilder, type SceneBlockData } from '../lib/virtual-world/scene-builder'
import { apiClient, extractData, extractPaginated } from '@/services/api-client'
import type { VirtualWorldScene, VirtualWorldSceneBlock } from './modules/virtual-world/types'
import styles from './world-app.module.css'

// ── 常量 ──
const CAMERA_FOV = 50
const CAMERA_NEAR = 0.1
const CAMERA_FAR = 500
const GRID_SIZE = 64
const FPS_TARGET = 60

// ── API ──

async function fetchActiveScene(): Promise<VirtualWorldScene | null> {
  try {
    const { items } = extractPaginated(
      (await apiClient.get('/virtualworld/scenes', {
        params: { page: 1, pageSize: 100 },
      })) as unknown as { items: unknown[]; total: number },
    )
    return (items as VirtualWorldScene[]).find((s) => s.isActive) ?? null
  } catch {
    return null
  }
}

async function fetchSceneBlocks(sceneId: number): Promise<VirtualWorldSceneBlock[]> {
  try {
    return extractData(
      await apiClient.get(`/virtualworld/scenes/${sceneId}/blocks`),
    ) as VirtualWorldSceneBlock[]
  } catch {
    return []
  }
}

// ── 组件 ──

export default function WorldApp() {
  const containerRef = useRef<HTMLDivElement>(null)
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null)
  const sceneRef = useRef<THREE.Scene | null>(null)
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null)
  const controlsRef = useRef<OrbitControls | null>(null)
  const builderRef = useRef<SceneBuilder | null>(null)
  const animFrameRef = useRef<number>(0)
  const clockRef = useRef<THREE.Clock>(new THREE.Clock())

  const [status, setStatus] = useState('初始化中...')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [blockCount, setBlockCount] = useState(0)

  // ── 初始化 Three.js 场景 ──
  const initScene = useCallback((container: HTMLDivElement) => {
    const width = container.clientWidth
    const height = container.clientHeight

    // 渲染器
    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: true,
      premultipliedAlpha: false,
    })
    renderer.setSize(width, height)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.outputColorSpace = THREE.SRGBColorSpace
    renderer.toneMapping = THREE.AgXToneMapping
    renderer.toneMappingExposure = 1.0
    renderer.shadowMap.enabled = true
    renderer.shadowMap.type = THREE.PCFSoftShadowMap
    renderer.setClearColor(0x000000, 0)
    container.appendChild(renderer.domElement)
    rendererRef.current = renderer

    // 场景
    const scene = new THREE.Scene()
    sceneRef.current = scene

    // 相机
    const camera = new THREE.PerspectiveCamera(CAMERA_FOV, width / height, CAMERA_NEAR, CAMERA_FAR)
    camera.position.set(20, 25, 30)
    camera.lookAt(0, 0, 0)
    cameraRef.current = camera

    // 控制器
    const controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true
    controls.dampingFactor = 0.08
    controls.target.set(0, 0, 0)
    controls.maxPolarAngle = Math.PI / 2.05
    controls.minDistance = 5
    controls.maxDistance = 150
    controlsRef.current = controls

    // 灯光
    setupLights(scene)

    // 地面网格
    setupGrid(scene)

    // SceneBuilder
    const builder = new SceneBuilder(scene)
    builderRef.current = builder

    return { renderer, scene, camera, controls, builder }
  }, [])

  // ── 灯光配置 ──
  function setupLights(scene: THREE.Scene): void {
    // 环境光
    scene.add(new THREE.AmbientLight(0xffffff, 0.5))

    // 半球光
    scene.add(new THREE.HemisphereLight(0xddeeff, 0x202020, 0.4))

    // 主定向光 + 阴影
    const dirLight = new THREE.DirectionalLight(0xffffff, 1.0)
    dirLight.position.set(30, 50, 30)
    dirLight.castShadow = true
    dirLight.shadow.mapSize.width = 1024
    dirLight.shadow.mapSize.height = 1024
    dirLight.shadow.camera.near = 0.5
    dirLight.shadow.camera.far = 150
    dirLight.shadow.camera.left = -40
    dirLight.shadow.camera.right = 40
    dirLight.shadow.camera.top = 40
    dirLight.shadow.camera.bottom = -40
    dirLight.shadow.bias = -0.001
    scene.add(dirLight)
    scene.add(dirLight.target)

    // 补光
    const fillLight = new THREE.DirectionalLight(0xffeedd, 0.3)
    fillLight.position.set(-20, 20, 10)
    scene.add(fillLight)
  }

  // ── 地面网格 ──
  function setupGrid(scene: THREE.Scene): void {
    const gridHelper = new THREE.GridHelper(GRID_SIZE, GRID_SIZE, 0xcccccc, 0xe8e8e8)
    gridHelper.position.y = -0.01
    scene.add(gridHelper)

    // 阴影地面
    const groundGeo = new THREE.PlaneGeometry(GRID_SIZE, GRID_SIZE)
    const groundMat = new THREE.ShadowMaterial({ opacity: 0.15 })
    const ground = new THREE.Mesh(groundGeo, groundMat)
    ground.rotation.x = -Math.PI / 2
    ground.receiveShadow = true
    scene.add(ground)
  }

  // ── 自动适配相机到场景 ──
  function fitCameraToScene(camera: THREE.PerspectiveCamera, controls: OrbitControls, blocks: SceneBlockData[]): void {
    if (blocks.length === 0) return

    let minX = Infinity, maxX = -Infinity
    let minY = Infinity, maxY = -Infinity
    let minZ = Infinity, maxZ = -Infinity

    for (const b of blocks) {
      minX = Math.min(minX, b.posX)
      maxX = Math.max(maxX, b.posX)
      minY = Math.min(minY, b.posY)
      maxY = Math.max(maxY, b.posY)
      minZ = Math.min(minZ, b.posZ)
      maxZ = Math.max(maxZ, b.posZ)
    }

    const cx = (minX + maxX) / 2
    const cy = (minY + maxY) / 2
    const cz = (minZ + maxZ) / 2
    const radius = Math.max(maxX - minX, maxY - minY, maxZ - minZ) / 2
    const dist = Math.max(radius * 2.5, 15)

    camera.position.set(cx + dist * 0.7, cy + dist * 0.8, cz + dist)
    controls.target.set(cx, cy, cz)
    controls.update()
  }

  // ── 渲染循环 ──
  const startRenderLoop = useCallback(() => {
    const clock = clockRef.current
    clock.getDelta() // 丢弃首帧 delta

    const animate = () => {
      animFrameRef.current = requestAnimationFrame(animate)

      const delta = Math.min(clock.getDelta(), 0.1)
      controlsRef.current?.update()
      rendererRef.current?.render(sceneRef.current!, cameraRef.current!)
    }

    animFrameRef.current = requestAnimationFrame(animate)
  }, [])

  // ── 加载场景数据 ──
  const loadScene = useCallback(async () => {
    try {
      setLoading(true)
      setStatus('查找激活场景...')

      const scene = await fetchActiveScene()
      if (!scene) {
        setStatus('未找到激活场景，请在控制台激活一个场景')
        setLoading(false)
        return
      }

      setStatus(`加载场景: ${scene.name}...`)
      const blocks = await fetchSceneBlocks(scene.id)

      if (blocks.length === 0) {
        setStatus(`场景「${scene.name}」为空，请在场景搭建中放置方块`)
        setLoading(false)
        return
      }

      // 转换为 SceneBlockData 格式
      const blockData: SceneBlockData[] = blocks.map((b) => ({
        blockId: b.blockId,
        posX: b.posX,
        posY: b.posY,
        posZ: b.posZ,
        rotationY: b.rotationY,
        material: b.material || undefined,
      }))

      // 加载到场景
      builderRef.current?.loadFromBlocks(blockData)
      setBlockCount(blockData.length)

      // 适配相机
      if (cameraRef.current && controlsRef.current) {
        fitCameraToScene(cameraRef.current, controlsRef.current, blockData)
      }

      setStatus(`「${scene.name}」— ${blockData.length} 个方块`)
      setLoading(false)
    } catch (err) {
      const msg = err instanceof Error ? err.message : '加载失败'
      setError(msg)
      setLoading(false)
    }
  }, [])

  // ── 窗口 resize ──
  const handleResize = useCallback(() => {
    const container = containerRef.current
    if (!container || !rendererRef.current || !cameraRef.current) return

    const width = container.clientWidth
    const height = container.clientHeight
    if (width <= 0 || height <= 0) return

    cameraRef.current.aspect = width / height
    cameraRef.current.updateProjectionMatrix()
    rendererRef.current.setSize(width, height)
  }, [])

  // ── 初始化 ──
  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    initScene(container)
    startRenderLoop()
    loadScene()

    window.addEventListener('resize', handleResize)

    // Electron 可见性控制
    const cleanupVis = window.electronAPI?.world?.onVisibilityChange?.((visible: boolean) => {
      if (visible) {
        if (animFrameRef.current === 0) startRenderLoop()
      } else {
        cancelAnimationFrame(animFrameRef.current)
        animFrameRef.current = 0
      }
    })

    return () => {
      window.removeEventListener('resize', handleResize)
      cancelAnimationFrame(animFrameRef.current)
      cleanupVis?.()

      controlsRef.current?.dispose()
      rendererRef.current?.dispose()
      rendererRef.current?.domElement.remove()

      rendererRef.current = null
      sceneRef.current = null
      cameraRef.current = null
      controlsRef.current = null
      builderRef.current = null
    }
  }, [initScene, startRenderLoop, loadScene, handleResize])

  // ── 拖动窗口 ──
  const handleDragStart = useCallback((e: React.MouseEvent) => {
    if (e.button !== 0) return
    if (e.target instanceof HTMLButtonElement) return
    e.preventDefault()

    const onMove = (ev: MouseEvent) => {
      window.electronAPI?.world?.dragWindowBy(ev.movementX, ev.movementY)
    }
    const onUp = () => {
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
    }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
  }, [])

  // ── 缩放 ──
  const handleZoom = useCallback((factor: number) => {
    const camera = cameraRef.current
    const controls = controlsRef.current
    if (!camera || !controls) return

    const dir = new THREE.Vector3().subVectors(camera.position, controls.target)
    const dist = dir.length()
    const newDist = Math.max(5, Math.min(150, dist * factor))
    dir.normalize().multiplyScalar(newDist)
    camera.position.copy(controls.target).add(dir)
    controls.update()
  }, [])

  const handleZoomIn = useCallback(() => handleZoom(0.8), [handleZoom])
  const handleZoomOut = useCallback(() => handleZoom(1.25), [handleZoom])

  const handleClose = useCallback(() => {
    window.electronAPI?.world?.hide()
  }, [])

  return (
    <div ref={containerRef} className={styles.container}>
      {/* 顶部拖动栏 */}
      <div className={styles.topBar} onMouseDown={handleDragStart}>
        <span className={styles.topBarTitle}>🌍 虚拟世界</span>
        <div className={styles.topBarActions}>
          <Button
            type="text"
            size="small"
            icon={<ZoomInOutlined />}
            className={styles.topBarBtn}
            onClick={handleZoomIn}
          />
          <Button
            type="text"
            size="small"
            icon={<ZoomOutOutlined />}
            className={styles.topBarBtn}
            onClick={handleZoomOut}
          />
          <Button
            type="text"
            size="small"
            icon={<ReloadOutlined />}
            className={styles.topBarBtn}
            onClick={loadScene}
          />
          <Button
            type="text"
            size="small"
            icon={<CloseOutlined />}
            className={styles.topBarBtnClose}
            onClick={handleClose}
          />
        </div>
      </div>

      {/* 加载态 */}
      {loading && !error && (
        <div className={styles.overlay}>
          <Spin indicator={<LoadingOutlined className={styles.spinIcon} spin />} />
          <span className={styles.statusText}>{status}</span>
        </div>
      )}

      {/* 错误态 */}
      {error && (
        <div className={styles.overlay}>
          <div className={styles.errorIcon}>⚠️</div>
          <span className={styles.errorText}>{error}</span>
        </div>
      )}

      {/* 底部状态栏 */}
      {!loading && !error && (
        <div className={styles.statusBar}>
          <span className={styles.statusLabel}>{status}</span>
          <span className={styles.blockBadge}>{blockCount} 方块</span>
        </div>
      )}
    </div>
  )
}
