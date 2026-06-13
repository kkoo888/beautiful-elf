import { Typography } from 'antd'

interface PetScreenshotPreviewProps {
  /** 截图数据 URL，null 表示无截图 */
  screenshot: string | null
  /** 宠物窗口是否可见 */
  petVisible: boolean
  /** 点击预览区回调 */
  onClick?: () => void
}

/**
 * 宠物截图预览 - 纯展示组件
 * 接收截图和可见性作为 props，不包含 Card 包装和独立的 toggle 按钮
 */
export default function PetScreenshotPreview({
  screenshot,
  petVisible,
  onClick,
}: PetScreenshotPreviewProps) {
  return (
    <div
      style={{
        width: '100%',
        height: '100%',
        cursor: 'pointer',
        position: 'relative',
        overflow: 'hidden',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
      onClick={onClick}
    >
      {screenshot ? (
        <img
          src={screenshot}
          alt="宠物截图"
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'contain',
            transition: 'opacity 0.3s ease',
          }}
        />
      ) : (
        <div
          style={{
            textAlign: 'center',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 12,
          }}
        >
          {/* 半透明宠物图标 + 脉冲动画 */}
          <style>{`
            @keyframes pet-placeholder-pulse {
              0%, 100% { opacity: 0.35; transform: scale(1); }
              50% { opacity: 0.7; transform: scale(1.06); }
            }
          `}</style>
          <div
            style={{
              fontSize: 72,
              opacity: 0.45,
              animation: 'pet-placeholder-pulse 2.5s ease-in-out infinite',
              lineHeight: 1,
            }}
          >
            🐱
          </div>
          <Typography.Text
            type="secondary"
            style={{
              fontSize: 14,
              background:
                'linear-gradient(135deg, rgba(255,255,255,0.6) 0%, rgba(255,255,255,0.2) 100%)',
              padding: '4px 16px',
              borderRadius: 12,
            }}
          >
            点击下方按钮开启桌面宠物
          </Typography.Text>
        </div>
      )}

      {/* 不可见遮罩 */}
      {!petVisible && (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            background: 'rgba(0, 0, 0, 0.45)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            backdropFilter: 'blur(1px)',
          }}
        >
          <Typography.Text
            style={{
              color: '#fff',
              fontSize: 14,
              background: 'rgba(255,255,255,0.15)',
              padding: '6px 20px',
              borderRadius: 20,
            }}
          >
            宠物窗口已关闭
          </Typography.Text>
        </div>
      )}
    </div>
  )
}
