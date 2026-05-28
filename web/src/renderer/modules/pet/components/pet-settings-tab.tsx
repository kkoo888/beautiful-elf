import { useState, useCallback } from 'react'
import { Card, Space, Input, Slider, Select, InputNumber, Button, Typography, message } from 'antd'
import {
  FolderOpenOutlined,
  EyeOutlined,
  EyeInvisibleOutlined,
  SettingOutlined,
} from '@ant-design/icons'
import { DEFAULT_PET_SETTINGS, DECAY_SPEED_OPTIONS, type PetSettings } from '../types/pet'

export default function PetSettingsTab() {
  const [settings, setSettings] = useState<PetSettings>(DEFAULT_PET_SETTINGS)
  const [petVisible, setPetVisible] = useState(false)

  const updateSetting = useCallback(
    <K extends keyof PetSettings>(key: K, value: PetSettings[K]) => {
      setSettings((prev) => ({ ...prev, [key]: value }))
    },
    []
  )

  const handleTogglePet = useCallback(async () => {
    const api = window.electronAPI?.pet
    if (!api) return
    await api.toggle()
    setPetVisible((v) => !v)
    message.info(petVisible ? '宠物窗口已隐藏' : '宠物窗口已显示')
  }, [petVisible])

  const handleSaveSettings = useCallback(() => {
    // TODO: persist settings to store/backend
    message.success('设置已保存')
  }, [])

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="middle">
      <Card size="small" title="模型配置">
        <Space direction="vertical" style={{ width: '100%' }} size="small">
          <div>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              模型路径
            </Typography.Text>
            <Input
              placeholder="输入 3D 模型文件路径 (如 .glb / .gltf)"
              value={settings.modelPath}
              onChange={(e) => updateSetting('modelPath', e.target.value)}
              suffix={<FolderOpenOutlined style={{ color: '#999' }} />}
            />
          </div>
        </Space>
      </Card>

      <Card size="small" title="窗口设置">
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
              <Typography.Text>窗口透明度</Typography.Text>
              <Typography.Text type="secondary">
                {Math.round(settings.opacity * 100)}%
              </Typography.Text>
            </div>
            <Slider
              min={0.1}
              max={1}
              step={0.05}
              value={settings.opacity}
              onChange={(v) => updateSetting('opacity', v)}
            />
          </div>
        </Space>
      </Card>

      <Card size="small" title="宠物行为">
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <div>
            <Typography.Text>属性衰减速度</Typography.Text>
            <Select
              style={{ width: '100%', marginTop: 4 }}
              value={settings.decaySpeed}
              options={DECAY_SPEED_OPTIONS}
              onChange={(v) => updateSetting('decaySpeed', v)}
            />
          </div>
          <div>
            <Typography.Text>气泡频率 (秒)</Typography.Text>
            <InputNumber
              style={{ width: '100%', marginTop: 4 }}
              min={1}
              max={60}
              value={settings.bubbleFrequency}
              onChange={(v) => updateSetting('bubbleFrequency', v ?? 5)}
            />
          </div>
        </Space>
      </Card>

      <Card size="small" title="窗口控制">
        <Space wrap>
          <Button
            type={petVisible ? 'default' : 'primary'}
            icon={petVisible ? <EyeInvisibleOutlined /> : <EyeOutlined />}
            onClick={handleTogglePet}
          >
            {petVisible ? '关闭宠物窗口' : '打开宠物窗口'}
          </Button>
          <Button type="primary" icon={<SettingOutlined />} onClick={handleSaveSettings}>
            保存设置
          </Button>
        </Space>
      </Card>
    </Space>
  )
}
