import { useEffect, useRef, useState, useCallback } from 'react'
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

  // 初始化 3D 场景
  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const scene = new PetScene(container)
    sceneRef.current = scene

    scene
      .init()
      .then(() => {
        setReady(true)
        // 通知主窗口：宠物已就绪
        if (window.electronAPI?.pet) {
          window.electronAPI.pet.sendScreenshot('')
        }
      })
      .catch((err) => {
        console.error('[PetApp] init failed:', err)
        setError(err.message || '初始化失败')
      })

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

  // 监听主窗口请求属性
  useEffect(() => {
    if (!window.electronAPI?.pet) return

    const handler = () => {
      // 返回当前宠物状态给主窗口
      const ipcRenderer = (window as any).electronAPI?.pet
      // 通过 IPC 回传属性（如果需要）
    }

    // electron 暴露的 API 不直接支持 on，需要通过 preload 桥接
    // 这里预留接口
  }, [])

  return (
    <div
      ref={containerRef}
      style={{
        width: '100vw',
        height: '100vh',
        overflow: 'hidden',
        background: 'transparent',
      }}
    >
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
