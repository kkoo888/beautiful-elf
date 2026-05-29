import { useState, useCallback, useEffect } from 'react'
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
  Spin,
} from 'antd'
import {
  FolderOpenOutlined,
  EyeOutlined,
  EyeInvisibleOutlined,
  SettingOutlined,
  ReloadOutlined,
} from '@ant-design/icons'
import { useElectronApi } from '@/hooks'
import { DEFAULT_PET_SETTINGS, DECAY_SPEED_OPTIONS, type PetSettings } from '../types/pet'
import {
  scanModels,
  switchPetModel,
  loadPetSettings,
  savePetSettings,
  loadPetModelPath,
} from '../services/pet-api'

export default function PetSettingsTab() {
  const [settings, setSettings] = useState<PetSettings>(DEFAULT_PET_SETTINGS)
  const [petVisible, setPetVisible] = useState(false)
  const [loading, setLoading] = useState(true)
  const queryClient = useQueryClient()
  const { pet: petApi, dialog: dialogApi, isElectron } = useElectronApi()
  const [modelDir, setModelDir] = useState<string>('')

  // ── 启动时加载已保存的设置 ──
  useEffect(() => {
    void (async () => {
      try {
        const [saved, savedModelPath] = await Promise.all([
          loadPetSettings(),
          loadPetModelPath(),
        ])
        if (saved) {
          setSettings({
            modelPath: (saved.modelPath as string) ?? savedModelPath ?? DEFAULT_PET_SETTINGS.modelPath,
            opacity: (saved.opacity as number) ?? DEFAULT_PET_SETTINGS.opacity,
            decaySpeed: (saved.decaySpeed as PetSettings['decaySpeed']) ?? DEFAULT_PET_SETTINGS.decaySpeed,
            bubbleFrequency: (saved.bubbleFrequency as number) ?? DEFAULT_PET_SETTINGS.bubbleFrequency,
          })
          if (saved.modelDir) {
            setModelDir(saved.modelDir as string)
          }
        } else if (savedModelPath) {
          // 没有完整设置，但有模型路径（从 switch_model 保存的）
          setSettings((prev) => ({ ...prev, modelPath: savedModelPath }))
          // 从模型路径推导目录
          const dir = savedModelPath.substring(0, savedModelPath.lastIndexOf('/'))
          if (dir) setModelDir(dir)
        }
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  // ── 扫描模型（有目录时自动触发）──
  const { data: models = [], isLoading: modelsLoading } = useQuery({
    queryKey: ['pet-models', modelDir],
    queryFn: () => scanModels(modelDir),
    enabled: !!modelDir,
  })

  // ── 切换模型 ──
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

  // ── 持久化保存设置（防抖）──
  const persistTimer = useState<{ current: ReturnType<typeof setTimeout> | null }>({ current: null })[0]

  const persistSettings = useCallback(
    (next: PetSettings, dir: string) => {
      if (persistTimer.current) clearTimeout(persistTimer.current)
      persistTimer.current = setTimeout(() => {
        void savePetSettings({ ...next, modelDir: dir })
      }, 500)
    },
    [persistTimer]
  )

  const updateSetting = useCallback(
    <K extends keyof PetSettings>(key: K, value: PetSettings[K]) => {
      setSettings((prev) => {
        const next = { ...prev, [key]: value }
        persistSettings(next, modelDir)
        return next
      })
    },
    [modelDir, persistSettings]
  )

  const handleModelChange = useCallback(
    (modelPath: string) => {
      setSettings((prev) => {
        const next = { ...prev, modelPath }
        persistSettings(next, modelDir)
        return next
      })
      switchMutation.mutate(modelPath)
    },
    [modelDir, persistSettings, switchMutation]
  )

  const handleTogglePet = useCallback(async () => {
    if (!isElectron) {
      message.warning('当前环境不支持宠物窗口')
      return
    }
    await petApi.toggle()
    setPetVisible((v) => !v)
    message.info(petVisible ? '宠物窗口已隐藏' : '宠物窗口已显示')
  }, [petVisible, petApi, isElectron])

  const handleSelectModelDir = useCallback(async () => {
    const dir = await dialogApi.selectDirectory()
    if (dir) {
      setModelDir(dir)
      // 目录变更也持久化
      setSettings((prev) => {
        persistSettings(prev, dir)
        return prev
      })
      message.info(`已选择目录: ${dir}`)
    }
  }, [dialogApi, persistSettings])

  const handleSaveSettings = useCallback(() => {
    void savePetSettings({ ...settings, modelDir }).then(() => {
      message.success('设置已保存')
    })
  }, [settings, modelDir])

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 40 }}>
        <Spin tip="加载设置中..." />
      </div>
    )
  }

  return (
    <Space orientation="vertical" style={{ width: '100%' }} size="middle">
      <Card size="small" title="模型配置">
        <Space orientation="vertical" style={{ width: '100%' }} size="small">
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
        <Space orientation="vertical" style={{ width: '100%' }} size="middle">
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
        <Space orientation="vertical" style={{ width: '100%' }} size="middle">
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
