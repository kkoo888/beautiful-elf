import { useEffect, useRef, useState, useCallback } from 'react'
import { Spin } from 'antd'
import { LoadingOutlined } from '@ant-design/icons'
import { PetScene } from './modules/pet/scene/pet-scene'
import { loadPetModelPath, loadPetSettings } from './modules/pet/services/pet-api'

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

      await scene.loadModel(modelPath, onProgress)

      const vmdPath = deriveVmdPath(modelPath)
      if (vmdPath) {
        try {
          await scene.loadModelWithAnimation(modelPath, vmdPath, onProgress)
        } catch {
          // VMD 可选，静默忽略
        }
      }
      setStatus('模型加载完成')
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
        setReady(true)

        setStatus('读取模型配置...')
        const modelPath = await fetchModelPath()

        if (modelPath) {
          currentModelPathRef.current = modelPath
          setStatus(`加载模型: ${modelPath.split('/').pop() || modelPath}`)

          const onProgress = (pct: number, msg: string) => setStatus(msg)

          await scene.loadModel(modelPath, onProgress)

          const vmdPath = deriveVmdPath(modelPath)
          if (vmdPath) {
            setStatus(`尝试加载动画: ${vmdPath.split('/').pop() || vmdPath}`)
            try {
              await scene.loadModelWithAnimation(modelPath, vmdPath, onProgress)
              setStatus('模型+动画加载完成')
            } catch (vmdErr) {
              console.warn('[PetApp] VMD load failed, falling back to model-only:', vmdErr)
              setStatus('模型加载完成（无动画）')
            }
          } else {
            setStatus('模型加载完成')
          }
        } else {
          setStatus('未配置模型，请在设置中选择模型目录')
        }

        // 通知主窗口：宠物已就绪
        if (window.electronAPI?.pet) {
          window.electronAPI.pet.sendScreenshot('')
        }
      } catch (err: any) {
        console.error('[PetApp] init failed:', err)
        setError(err.message || '初始化失败')
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

  // 定期截图发给主窗口（使用 toDataURL 替代 toBlob+readAsDataURL，链路更短）
  useEffect(() => {
    if (!ready) return
    const scene = sceneRef.current
    if (!scene) return

    const timer = setInterval(() => {
      const dataUrl = scene.getScreenshotDataURL()
      if (dataUrl) {
        window.electronAPI?.pet?.sendScreenshot(dataUrl)
      }
    }, 1000)

    return () => clearInterval(timer)
  }, [ready])

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
        await scene.loadModel(modelPath, onProgress)

        const vmdPath = deriveVmdPath(modelPath)
        if (vmdPath) {
          try {
            await scene.loadModelWithAnimation(modelPath, vmdPath, onProgress)
          } catch { /* optional */ }
        }
        setStatus('模型加载完成')
      } else {
        setStatus('未配置模型')
      }
    } catch (err: any) {
      setError(err.message || '加载失败')
    } finally {
      setLoading(false)
    }
  }, [])

  return (
    <div
      ref={containerRef}
      style={{
        width: '100vw',
        height: '100vh',
        overflow: 'hidden',
        background: 'transparent',
        position: 'relative',
      }}
    >
      {/* 加载中状态 */}
      {loading && !error && (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            background: 'rgba(0,0,0,0.5)',
            gap: 12,
            zIndex: 10,
          }}
        >
          <Spin
            indicator={<LoadingOutlined style={{ fontSize: 32, color: 'rgba(255,255,255,0.8)' }} spin />}
          />
          <span style={{ color: 'rgba(255,255,255,0.7)', fontSize: 13 }}>{status}</span>
        </div>
      )}

      {/* 状态提示 */}
      {status && !error && !loading && (
        <div
          style={{
            position: 'absolute',
            bottom: 8,
            left: 8,
            right: 8,
            color: 'rgba(255,255,255,0.6)',
            fontSize: 11,
            textAlign: 'center',
            pointerEvents: 'none',
            textShadow: '0 1px 2px rgba(0,0,0,0.5)',
          }}
        >
          {status}
        </div>
      )}

      {/* 错误状态 */}
      {error && (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            background: 'rgba(0,0,0,0.7)',
            gap: 16,
            zIndex: 20,
          }}
        >
          <div style={{ fontSize: 48, opacity: 0.6 }}>⚠️</div>
          <span style={{ color: '#ff4d4f', fontSize: 14, padding: '0 24px', textAlign: 'center' }}>
            宠物加载失败
          </span>
          <span
            style={{
              color: 'rgba(255,255,255,0.5)',
              fontSize: 12,
              padding: '0 24px',
              textAlign: 'center',
              maxWidth: 300,
            }}
          >
            {error}
          </span>
          <button
            onClick={handleRetry}
            style={{
              marginTop: 4,
              padding: '6px 20px',
              border: '1px solid rgba(255,255,255,0.3)',
              borderRadius: 4,
              background: 'rgba(255,255,255,0.1)',
              color: 'rgba(255,255,255,0.8)',
              cursor: 'pointer',
              fontSize: 13,
            }}
          >
            重试
          </button>
        </div>
      )}
    </div>
  )
}
