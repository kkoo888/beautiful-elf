import { useEffect, useState, useCallback } from 'react'
import { Card, Typography, Button } from 'antd'
import { EyeOutlined, EyeInvisibleOutlined } from '@ant-design/icons'

export default function PetScreenshotPreview() {
  const [screenshot, setScreenshot] = useState<string | null>(null)
  const [petVisible, setPetVisible] = useState(false)

  useEffect(() => {
    const api = window.electronAPI?.pet
    if (!api) return

    api.onScreenshotUpdate((data: string) => {
      setScreenshot(data)
    })

    api.onVisibilityChange((visible: boolean) => {
      setPetVisible(visible)
    })

    return () => {
      // Electron IPC listeners are cleaned up when window closes
    }
  }, [])

  const handleTogglePet = useCallback(async () => {
    await window.electronAPI?.pet?.toggle()
  }, [])

  return (
    <Card
      size="small"
      title="宠物窗口预览"
      extra={
        <Button
          size="small"
          type="link"
          icon={petVisible ? <EyeOutlined /> : <EyeInvisibleOutlined />}
          onClick={handleTogglePet}
        >
          {petVisible ? '隐藏' : '显示'}
        </Button>
      }
    >
      <div
        style={{
          width: '100%',
          height: 200,
          borderRadius: 8,
          overflow: 'hidden',
          background: '#1a1a2e',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          cursor: 'pointer',
          position: 'relative',
        }}
        onClick={handleTogglePet}
      >
        {screenshot ? (
          <img
            src={screenshot}
            alt="宠物截图"
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'contain',
            }}
          />
        ) : (
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 48, marginBottom: 8 }}>🐱</div>
            <Typography.Text type="secondary">
              {petVisible ? '等待截图...' : '点击打开宠物窗口'}
            </Typography.Text>
          </div>
        )}
        {!petVisible && (
          <div
            style={{
              position: 'absolute',
              inset: 0,
              background: 'rgba(0,0,0,0.4)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <Typography.Text style={{ color: '#fff' }}>宠物窗口已关闭</Typography.Text>
          </div>
        )}
      </div>
    </Card>
  )
}
