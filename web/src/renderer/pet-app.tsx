import { useEffect, useRef, useState } from 'react'
import { PetScene } from './modules/pet/scene/pet-scene'

/**
 * 宠物窗口主应用
 * 独立的 Electron 渲染进程，负责 3D 宠物渲染
 */
export default function PetApp() {
  const containerRef = useRef<HTMLDivElement>(null)
  const sceneRef = useRef<PetScene | null>(null)
  const [ready, setReady] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [status, setStatus] = useState<string>('初始化中...')

  // 初始化 3D 场景 + 加载模型
  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const scene = new PetScene(container)
    sceneRef.current = scene

    const initPet = async () => {
      try {
        setStatus('初始化 3D 场景...')
        await scene.init()
        setReady(true)

        // 从后端读取已保存的模型路径
        setStatus('读取模型配置...')
        const modelPath = await fetchModelPath()

        if (modelPath) {
          setStatus(`加载模型: ${modelPath.split('/').pop() || modelPath}`)
          await scene.loadModel(modelPath)
          setStatus('模型加载完成')
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
        const dataUrl = canvas.toDataURL('image/png')
        window.electronAPI?.pet?.sendScreenshot(dataUrl)
      } catch {
        // 跨域等异常静默处理
      }
    }, 500)

    return () => clearInterval(timer)
  }, [ready])

  // 监听主窗口请求模型切换
  useEffect(() => {
    if (!window.electronAPI?.pet) return

    const cleanup = window.electronAPI.pet.onVisibilityChange(async (visible: boolean) => {
      if (visible && sceneRef.current) {
        // 每次窗口显示时检查模型是否有更新
        try {
          const modelPath = await fetchModelPath()
          if (modelPath) {
            await sceneRef.current.loadModel(modelPath)
          }
        } catch (e) {
          console.warn('[PetApp] refresh model failed:', e)
        }
      }
    })

    return () => cleanup?.()
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
      {/* 状态提示（开发阶段可见，生产可隐藏） */}
      {status && !error && (
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
      {error && (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#ff4d4f',
            fontSize: 14,
            background: 'rgba(0,0,0,0.6)',
            padding: 20,
            textAlign: 'center',
          }}
        >
          {error}
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
      const value = body?.data?.key_value
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
      return body?.data?.key_value ?? null
    }
  } catch {
    // 都没有
  }

  return null
}
