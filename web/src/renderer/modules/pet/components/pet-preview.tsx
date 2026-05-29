import { Typography } from 'antd'
import { useElectronApi } from '@/hooks'

interface PetPreviewProps {
  screenshot: string | null
  visible: boolean
  onToggle: () => void
}

/**
 * 宠物预览区
 * - 已启动：显示 Live2D 模型截图
 * - 未启动：显示占位提示
 */
export default function PetPreview({ screenshot, visible, onToggle }: PetPreviewProps) {
  return (
    <div
      style={{
        width: '100%',
        height: 320,
        borderRadius: 12,
        overflow: 'hidden',
        background: visible
          ? 'linear-gradient(135deg, #f5f0ff 0%, #ede4ff 100%)'
          : 'var(--ant-color-fill-quaternary)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        cursor: 'pointer',
        position: 'relative',
        border: '1px solid var(--ant-color-border-secondary)',
      }}
      onClick={onToggle}
    >
      {visible && screenshot ? (
        <img
          src={screenshot}
          alt="宠物预览"
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'contain',
          }}
        />
      ) : visible ? (
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 64, marginBottom: 12 }}>🐱</div>
          <Typography.Text type="secondary">等待截图...</Typography.Text>
        </div>
      ) : (
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 48, marginBottom: 12, opacity: 0.4 }}>🐾</div>
          <Typography.Text type="secondary" style={{ fontSize: 16 }}>
            宠物窗口未启动
          </Typography.Text>
          <br />
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            点击上方按钮打开
          </Typography.Text>
        </div>
      )}
    </div>
  )
}
