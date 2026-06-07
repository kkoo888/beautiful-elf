import React from 'react'
import { Switch, Slider, Select, Space, Typography } from 'antd'
import type { FrameChangeConfig } from '../types/visual'

const { Text } = Typography

interface FrameSettingsProps {
  config: FrameChangeConfig
  onChange: (config: FrameChangeConfig) => void
}

const sensitivityOptions = [
  { label: '低', value: 'low' },
  { label: '中', value: 'medium' },
  { label: '高', value: 'high' },
]

export const FrameSettings: React.FC<FrameSettingsProps> = ({ config, onChange }) => {
  const update = (patch: Partial<FrameChangeConfig>) => {
    onChange({ ...config, ...patch })
  }

  return (
    <div className="frame-settings">
      <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
        <Space style={{ justifyContent: 'space-between', width: '100%' }}>
          <Text>帧变化检测</Text>
          <Switch checked={config.enabled} onChange={(checked) => update({ enabled: checked })} />
        </Space>

        {config.enabled && (
          <>
            <div>
              <Text type="secondary" style={{ fontSize: 12 }}>
                差异阈值: {config.threshold}
              </Text>
              <Slider
                min={1}
                max={20}
                value={config.threshold}
                onChange={(val) => update({ threshold: val })}
                marks={{ 1: '1', 5: '5', 10: '10', 15: '15', 20: '20' }}
              />
            </div>

            <Space style={{ justifyContent: 'space-between', width: '100%' }}>
              <Text type="secondary" style={{ fontSize: 12 }}>
                灵敏度
              </Text>
              <Select
                value={config.sensitivity}
                options={sensitivityOptions}
                onChange={(val) => update({ sensitivity: val })}
                style={{ width: 100 }}
                size="small"
              />
            </Space>
          </>
        )}
      </Space>
    </div>
  )
}
