import React from 'react'
import { Button, Tag, Typography, Empty, Space } from 'antd'
import { ReloadOutlined, CameraOutlined } from '@ant-design/icons'
import type { CaptureResult } from '../types/visual'

const { Text } = Typography

interface CapturePreviewProps {
  capture: CaptureResult | null
  onRecapture: () => void
}

const modeLabels: Record<string, { text: string; color: string }> = {
  fullscreen: { text: '全屏', color: 'blue' },
  region: { text: '选区', color: 'green' },
}

export const CapturePreview: React.FC<CapturePreviewProps> = ({ capture, onRecapture }) => {
  if (!capture) {
    return (
      <div className="capture-preview-empty">
        <Empty
          image={<CameraOutlined style={{ fontSize: 48, color: '#aaa' }} />}
          description="尚未截图"
        >
          <Button type="primary" icon={<CameraOutlined />} onClick={onRecapture}>
            开始截图
          </Button>
        </Empty>
      </div>
    )
  }

  const { text, color } = modeLabels[capture.mode] || modeLabels.fullscreen
  const timeStr = new Date(capture.timestamp).toLocaleTimeString()

  return (
    <div className="capture-preview">
      <div className="capture-preview-header">
        <Space>
          <Tag color={color}>{text}</Tag>
          <Text type="secondary">{timeStr}</Text>
        </Space>
        <Button icon={<ReloadOutlined />} size="small" onClick={onRecapture}>
          重新截图
        </Button>
      </div>
      <div className="capture-preview-image">
        <img
          src={capture.imageData}
          alt="截图预览"
          style={{ width: '100%', borderRadius: 8, border: '1px solid #333' }}
        />
      </div>
    </div>
  )
}
