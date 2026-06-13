import { useEffect, useRef, useState, useCallback } from 'react'
import { Spin } from 'antd'
import { LoadingOutlined } from '@ant-design/icons'
import { PetScene } from './modules/pet/scene/pet-scene'
import { loadPetModelPath, loadPetSettings } from './modules/pet/services/pet-api'

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

        // 从后端读取已保存的模型路径
        setStatus('读取模型配置...')
        const modelPath = await fetchModelPath()

        if (modelPath) {
          currentModelPathRef.current = modelPath
          setStatus(`加载模型: ${modelPath.split('/').pop() || modelPath}`)

          // 先加载模型
          await scene.loadModel(modelPath)

          // 检查同目录下是否有同名 .vmd 文件
          const vmdPath = deriveVmdPath(modelPath)
          if (vmdPath) {
            setStatus(`尝试加载动画: ${vmdPath.split('/').pop() || vmdPath}`)
            try {
              await scene.loadModelWithAnimation(modelPath, vmdPath)
              setStatus('模型+动画加载完成')
            } catch (vmdErr) {
              // VMD 加载失败，模型本身已加载，降级处理
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
    const cleanup = window.electronAPI?.pet?.onVisibilityChange((visible: boolean) => {
      scene.setVisible(visible)
    })

    return () => {
      cleanup?.()
      scene.dispose()
      sceneRef.current = null
    }
  }, [])

  // 定期截图发给主窗口
  useEffect(() => {
    if (!ready) return
    const scene = sceneRef.current
    if (!scene) return

    const timer = setInterval(() => {
      const canvas = scene.getCanvas()
      if (!canvas) return
      try {
        // 使用 toBlob 异步截图，避免同步 toDataURL 阻塞渲染线程
        canvas.toBlob((blob) => {
          if (!blob) return
          const reader = new FileReader()
          reader.onload = () => {
            window.electronAPI?.pet?.sendScreenshot(reader.result as string)
          }
          reader.readAsDataURL(blob)
        }, 'image/png')
      } catch {
        // 跨域等异常静默处理
      }
    }, 500)

    return () => clearInterval(timer)
  }, [ready])

  // 监听主窗口请求模型切换（通过可见性变化）
  useEffect(() => {
    if (!window.electronAPI?.pet) return

    const cleanup = window.electronAPI.pet.onVisibilityChange(async (visible: boolean) => {
      if (visible && sceneRef.current) {
        // 每次窗口显示时检查模型是否有更新
        try {
          const modelPath = await fetchModelPath()
          if (modelPath && modelPath !== currentModelPathRef.current) {
            currentModelPathRef.current = modelPath
            setStatus(`切换模型: ${modelPath.split('/').pop() || modelPath}`)
            setLoading(true)
            try {
              await sceneRef.current.loadModel(modelPath)

              const vmdPath = deriveVmdPath(modelPath)
              if (vmdPath) {
                try {
                  await sceneRef.current.loadModelWithAnimation(modelPath, vmdPath)
                } catch {
                  // VMD 可选，静默忽略
                }
              }
            } finally {
              setLoading(false)
            }
          }
        } catch (e) {
          console.warn('[PetApp] refresh model failed:', e)
        }
      }
    })

    return () => cleanup?.()
  }, [])

  // 监听模型切换通知（主窗口切换模型时触发）
  useEffect(() => {
    if (!window.electronAPI?.pet) return

    const cleanup = window.electronAPI.pet.onModelChanged(async () => {
      if (!sceneRef.current) return

      try {
        const modelPath = await fetchModelPath()
        if (modelPath && modelPath !== currentModelPathRef.current) {
          currentModelPathRef.current = modelPath
          setStatus(`切换模型: ${modelPath.split('/').pop() || modelPath}`)
          setLoading(true)
          try {
            await sceneRef.current.loadModel(modelPath)

            const vmdPath = deriveVmdPath(modelPath)
            if (vmdPath) {
              try {
                await sceneRef.current.loadModelWithAnimation(modelPath, vmdPath)
              } catch {
                // VMD 可选，静默忽略
              }
            }
            setStatus('模型加载完成')
          } finally {
            setLoading(false)
          }
        }
      } catch (e) {
        console.warn('[PetApp] model reload failed:', e)
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
        await scene.loadModel(modelPath)

        const vmdPath = deriveVmdPath(modelPath)
        if (vmdPath) {
          try {
            await scene.loadModelWithAnimation(modelPath, vmdPath)
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

      {/* 状态提示（开发阶段可见，生产可隐藏） */}
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

/**
 * 从后端读取已保存的模型路径
 * 优先读 pet_settings（含 modelPath），回退到 pet_model_path
 */
async function fetchModelPath(): Promise<string | null> {
  const base = 'http://localhost:8000/api/v1'

  try {
    // 先尝试读 pet_settings 里的 modelPath
    const settingsResp = await fetch(`${base}/configs/pet_settings`)
    if (settingsResp.ok) {
      const body = await settingsResp.json()
      const value = body?.data?.keyValue
      if (value) {
        const parsed = JSON.parse(value)
        if (parsed.modelPath) return parsed.modelPath
      }
    }
  } catch {
    // pet_settings 不存在，继续
  }

  try {
    // 回退：读 pet_model_path（switch_model 保存的）
    const resp = await fetch(`${base}/configs/pet_model_path`)
    if (resp.ok) {
      const body = await resp.json()
      return body?.data?.keyValue ?? null
    }
  } catch {
    // 都没有
  }

  // 也尝试通过 API 服务获取
  try {
    return await loadPetModelPath()
  } catch {
    // 所有方式都失败
  }

  return null
}

/**
 * 从模型路径推导同名 VMD 路径
 * 例如 /models/test.pmx → /models/test.vmd
 */
function deriveVmdPath(modelPath: string): string | null {
  if (!modelPath) return null

  // 去除扩展名后追加 .vmd
  const lastDot = modelPath.lastIndexOf('.')
  if (lastDot <= 0) return null

  const baseWithoutExt = modelPath.substring(0, lastDot)
  return `${baseWithoutExt}.vmd`
}
