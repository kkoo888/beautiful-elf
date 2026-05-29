import { useState, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Card,
  Space,
  Input,
  Slider,
  Select,
  InputNumber,
  Button,
  Typography,
  Descriptions,
  message,
} from 'antd'
import {
  FolderOpenOutlined,
  ReloadOutlined,
  SettingOutlined,
} from '@ant-design/icons'
import { useElectronApi } from '@/hooks'
import { DEFAULT_PET_SETTINGS, DECAY_SPEED_OPTIONS, type PetSettings } from '../types/pet'
import { scanModels, switchPetModel } from '../services/pet-api'

export default function PetSettingsTab() {
  const [settings, setSettings] = useState<PetSettings>(DEFAULT_PET_SETTINGS)
  const queryClient = useQueryClient()
  const { dialog: dialogApi } = useElectronApi()
  const [modelDir, setModelDir] = useState<string>('')

  const { data: models = [], isLoading: modelsLoading } = useQuery({
    queryKey: ['pet-models', modelDir],
    queryFn: () => scanModels(modelDir),
    enabled: !!modelDir,
  })

  const switchMutation = useMutation({
    mutationFn: switchPetModel,
    onSuccess: () => {
      message.success('模型已切换，宠物窗口将重新加载')
      queryClient.invalidateQueries({ queryKey: ['pet-models'] })
    },
    onError: () => {
      message.error('模型切换失败')
    },
  })

  const updateSetting = useCallback(
    <K extends keyof PetSettings>(key: K, value: PetSettings[K]) => {
      setSettings((prev) => ({ ...prev, [key]: value }))
    },
    []
  )

  const handleModelChange = useCallback(
    (modelPath: string) => {
      updateSetting('modelPath', modelPath)
      switchMutation.mutate(modelPath)
    },
    [updateSetting, switchMutation]
  )

  const handleSelectModelDir = useCallback(async () => {
    const dir = await dialogApi.selectDirectory()
    if (dir) {
      setModelDir(dir)
      message.info(`已选择目录: ${dir}`)
    }
  }, [dialogApi])

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
              模型目录
            </Typography.Text>
            <Space style={{ width: '100%', marginTop: 4 }}>
              <Input
                placeholder="点击右侧按钮选择模型目录"
                value={modelDir}
                readOnly
                style={{ flex: 1 }}
              />
              <Button icon={<FolderOpenOutlined />} onClick={handleSelectModelDir}>
                选择目录
              </Button>
              <Button
                icon={<ReloadOutlined />}
                onClick={() => queryClient.invalidateQueries({ queryKey: ['pet-models', modelDir] })}
                disabled={!modelDir}
              >
                刷新
              </Button>
            </Space>
          </div>

          <div>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              选择模型
            </Typography.Text>
            <Select
              style={{ width: '100%', marginTop: 4 }}
              placeholder={modelDir ? '选择模型文件' : '请先选择模型目录'}
              value={settings.modelPath || undefined}
              onChange={handleModelChange}
              loading={modelsLoading}
              options={models.map((m) => ({ label: m.name, value: m.path }))}
              notFoundContent={modelsLoading ? '扫描中...' : modelDir ? '目录下无模型文件' : '请先选择目录'}
              disabled={!modelDir}
            />
          </div>

          {settings.modelPath && (
            <Descriptions size="small" column={1} bordered style={{ marginTop: 8 }}>
              <Descriptions.Item label="当前模型">
                {settings.modelPath.split('/').pop() || settings.modelPath}
              </Descriptions.Item>
              <Descriptions.Item label="路径">{settings.modelPath}</Descriptions.Item>
            </Descriptions>
          )}
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

      <Card size="small" title="设置操作">
        <Button type="primary" icon={<SettingOutlined />} onClick={handleSaveSettings} block>
          保存设置
        </Button>
      </Card>
    </Space>
  )
}
