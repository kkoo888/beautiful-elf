import { useEffect, useRef, useState, useCallback } from 'react'
import { Spin } from 'antd'
import { LoadingOutlined } from '@ant-design/icons'
import { PetScene } from './modules/pet/scene/pet-scene'
import { loadPetModelPath, loadPetSettings } from './modules/pet/services/pet-api'
import { apiClient } from '@/services/api-client'
import styles from './pet-app.module.css'

/**
 * 从后端读取已保存的模型路径
 * 优先读 pet_settings（含 modelPath），回退到 pet_model_path
 */
async function fetchModelPath(): Promise<string | null> {
  try {
    const settings = await loadPetSettings()
    const path = settings?.modelPath as string | undefined
    if (path) return path
  } catch { /* pet_settings 不存在 */ }

  try {
    return await loadPetModelPath()
  } catch { /* 都没有 */ }

  return null
}

/**
 * 从模型路径推导同名 VMD 路径
 * 例如 /models/test.pmx → /models/test.vmd
 */
function deriveVmdPath(modelPath: string): string | null {
  if (!modelPath) return null
  const lastDot = modelPath.lastIndexOf('.')
  if (lastDot <= 0) return null
  return `${modelPath.substring(0, lastDot)}.vmd`
}

/**
 * 宠物窗口主应用
 * 独立的 Electron 渲染进程，负责 3D 宠物渲染
 */
export default function PetApp() {
  const containerRef = useRef<HTMLDivElement>(null)
  const sceneRef = useRef<PetScene | null>(null)
  const currentModelPathRef = useRef<string | null>(null)
  const [ready, setReady] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [status, setStatus] = useState<string>('初始化中...')
  const [loading, setLoading] = useState(false)

  /**
   * 统一的模型重载逻辑（消除 3 处重复调用）
   * 检查模型路径是否有变化，有变化则重新加载
   */
  const reloadIfNeeded = useCallback(async (scene: PetScene, reason: string) => {
    try {
      const modelPath = await fetchModelPath()
      if (!modelPath || modelPath === currentModelPathRef.current) return

      currentModelPathRef.current = modelPath
      setStatus(`切换模型: ${modelPath.split('/').pop() || modelPath}`)
      setLoading(true)

      const onProgress = (pct: number, msg: string) => setStatus(msg)

      const modelUrl = modelPath.startsWith('file:')
        ? modelPath
        : `file:///${modelPath.replace(/\\/g, '/')}`

      const vmdPath = deriveVmdPath(modelUrl)
      if (vmdPath) {
        try {
          await scene.loadModelWithAnimation(modelUrl, vmdPath, onProgress)
          setStatus('模型+动画加载完成')
        } catch {
          await scene.loadModel(modelUrl, onProgress)
          setStatus('模型加载完成（无动画）')
        }
      } else {
        await scene.loadModel(modelUrl, onProgress)
        setStatus('模型加载完成')
      }
    } catch (e) {
      console.warn(`[PetApp] reloadIfNeeded (${reason}) failed:`, e)
    } finally {
      setLoading(false)
    }
  }, [])

  // 初始化 3D 场景 + 加载模型
  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const scene = new PetScene(container)
    sceneRef.current = scene

    const initPet = async () => {
      try {
        setLoading(true)
        setStatus('初始化 3D 场景...')
        await scene.init()

        setStatus('读取模型配置...')
        const modelPath = await fetchModelPath()

        if (modelPath) {
          currentModelPathRef.current = modelPath
          setStatus(`加载模型: ${modelPath.split('/').pop() || modelPath}`)

          const onProgress = (pct: number, msg: string) => setStatus(msg)

          // Electron 中本地文件需要 file:// 前缀
          const modelUrl = modelPath.startsWith('file:')
        ? modelPath
        : `file:///${modelPath.replace(/\\/g, '/')}`

          const vmdPath = deriveVmdPath(modelUrl)
          if (vmdPath) {
            setStatus(`尝试加载动画: ${vmdPath.split('/').pop() || vmdPath}`)
            try {
              await scene.loadModelWithAnimation(modelUrl, vmdPath, onProgress)
              setStatus('模型+动画加载完成')
            } catch (vmdErr) {
              console.warn('[PetApp] VMD load failed, falling back to model-only:', vmdErr)
              await scene.loadModel(modelUrl, onProgress)
              setStatus('模型加载完成（无动画）')
            }
          } else {
            await scene.loadModel(modelUrl, onProgress)
            setStatus('模型加载完成')
          }
        } else {
          setStatus('未配置模型，请在设置中选择模型目录')
        }

        // 模型加载完成后再启动截图（避免截到空白画面）
        setReady(true)


      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : '初始化失败'
        console.error('[PetApp] init failed:', err)
        setError(msg)
      } finally {
        setLoading(false)
      }
    }

    initPet()

    // 可见性变化 → 控制渲染帧率
    const cleanupVis = window.electronAPI?.pet?.onVisibilityChange((visible: boolean) => {
      scene.setVisible(visible)
    })

    // 鼠标追踪 → 驱动头部/眼球跟随
    const cleanupMouse = window.electronAPI?.pet?.onGlobalMouseMove((pos) => {
      scene.setMousePosition(pos.x, pos.y)
    })

    return () => {
      cleanupVis?.()
      cleanupMouse?.()
      scene.dispose()
      sceneRef.current = null
    }
  }, [])

  // 监听手动截图请求（主窗口点击“截图”按钮触发）
  // 对齐图片画廊模式：canvas → blob → FormData → POST 后端
  useEffect(() => {
    if (!window.electronAPI?.pet) return
    const cleanup = window.electronAPI.pet.onRequestScreenshot(() => {
      const scene = sceneRef.current
      if (!scene) return
      scene.getScreenshotBlob(async (blob) => {
        if (!blob) return
        const formData = new FormData()
        formData.append('file', blob, 'latest.png')
        try {
          await apiClient.post('/pets/screenshot/upload', formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
          })
        } catch (e) {
          console.warn('[PetApp] screenshot upload failed:', e)
        }
      })
    })
    return () => cleanup?.()
  }, [])

  // 监听可见性变化 → 检查模型更新
  useEffect(() => {
    if (!window.electronAPI?.pet) return

    const cleanup = window.electronAPI.pet.onVisibilityChange(async (visible: boolean) => {
      if (visible && sceneRef.current) {
        await reloadIfNeeded(sceneRef.current, 'visibility-change')
      }
    })

    return () => cleanup?.()
  }, [reloadIfNeeded])

  // 监听模型切换通知（设置页面切换了模型路径）
  useEffect(() => {
    if (!window.electronAPI?.pet) return

    const cleanup = window.electronAPI.pet.onModelChanged(async () => {
      if (sceneRef.current) {
        await reloadIfNeeded(sceneRef.current, 'model-changed')
      }
    })

    return () => cleanup?.()
  }, [reloadIfNeeded])

  // 监听强制重载通知（控制面板点击刷新/重载模型）
  useEffect(() => {
    if (!window.electronAPI?.pet) return

    const cleanup = window.electronAPI.pet.onForceReload(async () => {
      const scene = sceneRef.current
      if (!scene || !scene.isLoaded) return

      try {
        setLoading(true)
        await scene.reloadModel((pct, msg) => setStatus(msg))
        setStatus('模型重载完成')
      } catch (e) {
        console.warn('[PetApp] force-reload failed:', e)
      } finally {
        setLoading(false)
      }
    })

    return () => cleanup?.()
  }, [])

  // 监听控制面板的缩放 / 动作指令（放大缩小 + 待机动画开关）
  useEffect(() => {
    if (!window.electronAPI?.pet) return

    const cleanups = [
      window.electronAPI.pet.onZoom((factor: number) => {
        sceneRef.current?.zoomBy(factor)
      }),
      window.electronAPI.pet.onSetIdle((enabled: boolean) => {
        sceneRef.current?.setIdleEnabled(enabled)
      }),
      window.electronAPI.pet.onResetZoom(() => {
        sceneRef.current?.resetZoom()
      }),
    ]

    return () => cleanups.forEach((c) => c?.())
  }, [])

  // 左键拖拽宠物窗口（移动窗口位置）；右键留给 OrbitControls 旋转，滚轮留给缩放
  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    let dragging = false

    const onMove = (e: MouseEvent) => {
      if (!dragging) return
      window.electronAPI?.pet?.dragWindowBy(e.movementX, e.movementY)
    }
    const onUp = () => {
      if (!dragging) return
      dragging = false
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
    }
    const onDown = (e: MouseEvent) => {
      if (e.button !== 0) return // 仅左键拖动
      if (e.target instanceof HTMLButtonElement) return // 不拦截按钮点击（如重试）
      dragging = true
      e.preventDefault()
      window.addEventListener('mousemove', onMove)
      window.addEventListener('mouseup', onUp)
    }

    container.addEventListener('mousedown', onDown)
    return () => {
      container.removeEventListener('mousedown', onDown)
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
    }
  }, [])

  // 重试加载
  const handleRetry = useCallback(async () => {
    setError(null)
    setLoading(true)
    setStatus('重试中...')

    const scene = sceneRef.current
    if (!scene) return

    try {
      const modelPath = await fetchModelPath()
      if (modelPath) {
        currentModelPathRef.current = modelPath
        const onProgress = (pct: number, msg: string) => setStatus(msg)
        const modelUrl = modelPath.startsWith('file:')
        ? modelPath
        : `file:///${modelPath.replace(/\\/g, '/')}`

        const vmdPath = deriveVmdPath(modelUrl)
        if (vmdPath) {
          try {
            await scene.loadModelWithAnimation(modelUrl, vmdPath, onProgress)
          } catch {
            await scene.loadModel(modelUrl, onProgress)
          }
        } else {
          await scene.loadModel(modelUrl, onProgress)
        }
        setStatus('模型加载完成')
      } else {
        setStatus('未配置模型')
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : '加载失败'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }, [])

  return (
    <div ref={containerRef} className={styles.container}>
      {/* 加载中状态 */}
      {loading && !error && (
        <div className={styles.loadingOverlay}>
          <Spin
            indicator={<LoadingOutlined style={{ fontSize: 32, color: 'rgba(255,255,255,0.8)' }} spin />}
          />
          <span className={styles.loadingText}>{status}</span>
        </div>
      )}

      {/* 错误状态 */}
      {error && (
        <div className={styles.errorOverlay}>
          <div className={styles.errorIcon}>⚠️</div>
          <span className={styles.errorMessage}>宠物加载失败</span>
          <span className={styles.errorDetail}>{error}</span>
          <button onClick={handleRetry} className={styles.retryBtn}>
            重试
          </button>
        </div>
      )}
    </div>
  )
}
