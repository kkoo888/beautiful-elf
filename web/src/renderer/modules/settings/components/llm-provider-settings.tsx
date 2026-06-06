/**
 * 大模型供应商配置组件 — 方案 A: 供应商+模型两表分离
 *
 * 改进:
 * 1. 模型不再塞 JSON，独立卡片管理
 * 2. 每个模型可单独启停、编辑、删除
 * 3. 添加模型时弹窗填写，不再手写 JSON
 * 4. 供应商卡片内嵌模型列表
 */

import { useCallback, useEffect, useState } from 'react'
import {
  Button,
  Card,
  Form,
  Input,
  InputNumber,
  Select,
  Space,
  Switch,
  Tag,
  Typography,
  Modal,
  Popconfirm,
  message,
  Empty,
  Tooltip,
  Divider,
  Collapse,
  Slider,
} from 'antd'
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  StarFilled,
  CloudOutlined,
  ApiOutlined,
  CheckCircleFilled,
  CloseCircleFilled,
  DownOutlined,
  RocketOutlined,
  EyeOutlined,
  ToolOutlined,
} from '@ant-design/icons'
import {
  getProviders,
  createProvider,
  updateProvider,
  toggleProvider,
  deleteProvider,
  createModel,
  updateModel,
  toggleModel,
  deleteModel,
} from '../services/settings-api'
import type {
  LLMProvider,
  LLMProviderPayload,
  LLMModel,
  LLMModelPayload,
  ProviderType,
} from '../types/settings'
import { PROVIDER_PRESETS } from '../types/settings'

const { Text } = Typography

const PROVIDER_TYPE_OPTIONS = [
  { label: 'OpenAI', value: 'openai' },
  { label: 'Claude (Anthropic)', value: 'claude' },
  { label: 'DeepSeek', value: 'deepseek' },
  { label: '通义千问', value: 'qwen' },
  { label: '小米 MiMo', value: 'xiaomi' },
  { label: '智谱 GLM', value: 'zhipu' },
  { label: '月之暗面', value: 'moonshot' },
  { label: 'Ollama (本地)', value: 'ollama' },
  { label: '自定义', value: 'custom' },
]

const TYPE_COLORS: Record<string, string> = {
  openai: '#10a37f',
  claude: '#d97706',
  deepseek: '#3b82f6',
  ollama: '#8b5cf6',
  qwen: '#f43f5e',
  xiaomi: '#ff6900',
  zhipu: '#2d5dea',
  moonshot: '#7c3aed',
  custom: '#6b7280',
}

/** 常用模型预设（添加模型时快速选择） */
const MODEL_PRESETS: Record<string, { modelName: string; displayName: string; contextLength: number }[]> = {
  openai: [
    { modelName: 'gpt-4o', displayName: 'GPT-4o', contextLength: 128000 },
    { modelName: 'gpt-4o-mini', displayName: 'GPT-4o Mini', contextLength: 128000 },
    { modelName: 'o3-mini', displayName: 'o3-mini', contextLength: 200000 },
  ],
  claude: [
    { modelName: 'claude-sonnet-4-20250514', displayName: 'Claude Sonnet 4', contextLength: 200000 },
    { modelName: 'claude-3-5-haiku-20241022', displayName: 'Claude 3.5 Haiku', contextLength: 200000 },
  ],
  deepseek: [
    { modelName: 'deepseek-chat', displayName: 'DeepSeek-V3', contextLength: 64000 },
    { modelName: 'deepseek-reasoner', displayName: 'DeepSeek-R1', contextLength: 64000 },
  ],
  ollama: [
    { modelName: 'qwen3.5:7b', displayName: 'Qwen3.5 7B', contextLength: 32768 },
    { modelName: 'llama3:8b', displayName: 'Llama3 8B', contextLength: 8192 },
  ],
  qwen: [
    { modelName: 'qwen-plus', displayName: '通义千问 Plus', contextLength: 131072 },
    { modelName: 'qwen-turbo', displayName: '通义千问 Turbo', contextLength: 131072 },
  ],
  xiaomi: [
    { modelName: 'mimo-v2.5-pro', displayName: 'MiMo V2.5 Pro', contextLength: 131072 },
    { modelName: 'mimo-v2-pro', displayName: 'MiMo V2 Pro', contextLength: 131072 },
    { modelName: 'mimo-v2-flash', displayName: 'MiMo V2 Flash', contextLength: 131072 },
  ],
  zhipu: [
    { modelName: 'glm-4-plus', displayName: 'GLM-4 Plus', contextLength: 128000 },
    { modelName: 'glm-4-flash', displayName: 'GLM-4 Flash', contextLength: 128000 },
  ],
  moonshot: [
    { modelName: 'moonshot-v1-128k', displayName: 'Moonshot V1 128K', contextLength: 128000 },
    { modelName: 'moonshot-v1-32k', displayName: 'Moonshot V1 32K', contextLength: 32000 },
  ],
}

export function LlmProviderSettings() {
  const [providers, setProviders] = useState<LLMProvider[]>([])
  const [loading, setLoading] = useState(true)

  // 供应商弹窗
  const [providerModalOpen, setProviderModalOpen] = useState(false)
  const [editingProvider, setEditingProvider] = useState<LLMProvider | null>(null)
  const [providerForm] = Form.useForm()

  // 模型弹窗
  const [modelModalOpen, setModelModalOpen] = useState(false)
  const [editingModel, setEditingModel] = useState<LLMModel | null>(null)
  const [modelProviderId, setModelProviderId] = useState<number>(0)
  const [modelForm] = Form.useForm()
  const [selectedProviderType, setSelectedProviderType] = useState<string>('')

  const loadProviders = useCallback(async () => {
    try {
      const list = await getProviders()
      setProviders(list)
    } catch (e: any) {
      message.error('加载供应商列表失败：' + (e.message || '未知错误'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void loadProviders() }, [loadProviders])

  // ── 供应商操作 ─────────────────────────────────────────

  const handleAddProvider = useCallback(() => {
    setEditingProvider(null)
    providerForm.resetFields()
    providerForm.setFieldsValue({ providerType: 'openai', isEnabled: true, isDefault: false })
    setSelectedProviderType('openai')
    setProviderModalOpen(true)
  }, [providerForm])

  const handleEditProvider = useCallback((p: LLMProvider) => {
    setEditingProvider(p)
    providerForm.setFieldsValue({
      name: p.name, providerType: p.providerType, baseUrl: p.baseUrl,
      apiKey: p.apiKey, description: p.description,
      isEnabled: p.isEnabled === 1, isDefault: p.isDefault === 1,
    })
    setSelectedProviderType(p.providerType)
    setProviderModalOpen(true)
  }, [providerForm])

  const handleSubmitProvider = useCallback(async () => {
    try {
      const values = await providerForm.validateFields()
      const payload: LLMProviderPayload = {
        name: values.name,
        providerType: values.providerType,
        baseUrl: values.baseUrl,
        apiKey: values.apiKey || '',
        isEnabled: values.isEnabled ? 1 : 0,
        isDefault: values.isDefault ? 1 : 0,
        description: values.description || '',
      }
      if (editingProvider) {
        await updateProvider(editingProvider.id, payload)
        message.success('供应商已更新')
      } else {
        await createProvider(payload)
        message.success('供应商已添加')
      }
      setProviderModalOpen(false)
      await loadProviders()
    } catch (e: any) {
      if (e.message) message.error(e.message)
    }
  }, [providerForm, editingProvider, loadProviders])

  const handleToggleProvider = useCallback(async (id: number) => {
    await toggleProvider(id)
    await loadProviders()
  }, [loadProviders])

  const handleDeleteProvider = useCallback(async (id: number) => {
    await deleteProvider(id)
    message.success('已删除')
    await loadProviders()
  }, [loadProviders])

  // ── 模型操作 ─────────────────────────────────────────

  const handleAddModel = useCallback((providerId: number, providerType: string) => {
    setEditingModel(null)
    setModelProviderId(providerId)
    setSelectedProviderType(providerType)
    modelForm.resetFields()
    modelForm.setFieldsValue({ isEnabled: true, temperature: 0.7, maxTokens: 4096, contextLength: 4096 })
    setModelModalOpen(true)
  }, [modelForm])

  const handleEditModel = useCallback((model: LLMModel) => {
    setEditingModel(model)
    setModelProviderId(model.providerId)
    modelForm.setFieldsValue({
      modelName: model.modelName,
      displayName: model.displayName,
      contextLength: model.contextLength,
      maxTokens: model.maxTokens,
      temperature: model.temperature,
      isEnabled: model.isEnabled === 1,
      remark: model.remark,
    })
    setModelModalOpen(true)
  }, [modelForm])

  const handleSubmitModel = useCallback(async () => {
    try {
      const values = await modelForm.validateFields()
      const payload: LLMModelPayload = {
        modelName: values.modelName,
        displayName: values.displayName || values.modelName,
        contextLength: values.contextLength || 4096,
        maxTokens: values.maxTokens || 4096,
        temperature: values.temperature ?? 0.7,
        isEnabled: values.isEnabled ? 1 : 0,
        remark: values.remark || '',
      }
      if (editingModel) {
        await updateModel(modelProviderId, editingModel.id, payload)
        message.success('模型已更新')
      } else {
        await createModel(modelProviderId, payload)
        message.success('模型已添加')
      }
      setModelModalOpen(false)
      await loadProviders()
    } catch (e: any) {
      if (e.message) message.error(e.message)
    }
  }, [modelForm, editingModel, modelProviderId, loadProviders])

  const handleToggleModel = useCallback(async (providerId: number, modelId: number) => {
    await toggleModel(providerId, modelId)
    await loadProviders()
  }, [loadProviders])

  const handleDeleteModel = useCallback(async (providerId: number, modelId: number) => {
    await deleteModel(providerId, modelId)
    message.success('模型已删除')
    await loadProviders()
  }, [loadProviders])

  const handlePresetSelect = useCallback((preset: { modelName: string; displayName: string; contextLength: number }) => {
    modelForm.setFieldsValue({
      modelName: preset.modelName,
      displayName: preset.displayName,
      contextLength: preset.contextLength,
    })
  }, [modelForm])

  const maskKey = (key: string) => {
    if (!key || key.length <= 8) return '****'
    return key.slice(0, 4) + '****' + key.slice(-4)
  }

  return (
    <div>
      {/* 头部 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Text type="secondary">配置大模型供应商和模型，模型可单独启停和管理</Text>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleAddProvider}>添加供应商</Button>
      </div>

      {/* 供应商列表 */}
      {providers.length === 0 && !loading ? (
        <Empty description="暂无供应商，点击上方按钮添加" style={{ padding: '48px 0' }} />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {providers.map((p) => (
            <Card
              key={p.id}
              size="small"
              style={{
                opacity: p.isEnabled ? 1 : 0.6,
                borderLeft: `3px solid ${TYPE_COLORS[p.providerType] || '#6b7280'}`,
              }}
            >
              {/* 供应商头部 */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ flex: 1 }}>
                  <Space align="center" size={8}>
                    <CloudOutlined style={{ color: TYPE_COLORS[p.providerType], fontSize: 18 }} />
                    <Text strong style={{ fontSize: 15 }}>{p.name}</Text>
                    <Tag color={TYPE_COLORS[p.providerType]}>
                      {PROVIDER_TYPE_OPTIONS.find((o) => o.value === p.providerType)?.label || p.providerType}
                    </Tag>
                    {p.isDefault === 1 && <Tag icon={<StarFilled />} color="gold">默认</Tag>}
                    <Tag
                      icon={p.isEnabled ? <CheckCircleFilled /> : <CloseCircleFilled />}
                      color={p.isEnabled ? 'success' : 'default'}
                    >
                      {p.isEnabled ? '已启用' : '已禁用'}
                    </Tag>
                  </Space>
                  <div style={{ marginTop: 4 }}>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      <ApiOutlined /> {p.baseUrl}　|　Key: {maskKey(p.apiKey)}
                    </Text>
                  </div>
                </div>
                <Space size={4}>
                  <Tooltip title={p.isEnabled ? '点击禁用' : '点击启用'}>
                    <Switch checked={p.isEnabled === 1} onChange={() => void handleToggleProvider(p.id)} size="small" />
                  </Tooltip>
                  <Tooltip title="编辑"><Button type="text" size="small" icon={<EditOutlined />} onClick={() => handleEditProvider(p)} /></Tooltip>
                  <Popconfirm title="确定删除此供应商及其所有模型？" onConfirm={() => void handleDeleteProvider(p.id)} okText="删除" cancelText="取消">
                    <Tooltip title="删除"><Button type="text" size="small" danger icon={<DeleteOutlined />} /></Tooltip>
                  </Popconfirm>
                </Space>
              </div>

              {/* 模型列表 */}
              <Divider style={{ margin: '8px 0' }} />
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                <Text type="secondary" style={{ fontSize: 12 }}>模型列表 ({p.models.length})</Text>
                <Button size="small" type="dashed" icon={<PlusOutlined />} onClick={() => handleAddModel(p.id, p.providerType)}>
                  添加模型
                </Button>
              </div>
              {p.models.length === 0 ? (
                <Text type="secondary" style={{ fontSize: 12 }}>暂无模型，点击上方添加</Text>
              ) : (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                  {p.models.map((m) => (
                    <Tag
                      key={m.id}
                      style={{
                        display: 'flex', alignItems: 'center', gap: 4, padding: '4px 8px',
                        opacity: m.isEnabled ? 1 : 0.5,
                      }}
                    >
                      <RocketOutlined style={{ fontSize: 12 }} />
                      <span>{m.displayName || m.modelName}</span>
                      {m.contextLength > 0 && <Text type="secondary" style={{ fontSize: 10 }}>{Math.round(m.contextLength / 1000)}k</Text>}
                      <Tooltip title={m.isEnabled ? '点击禁用' : '点击启用'}>
                        <Switch checked={m.isEnabled === 1} onChange={() => void handleToggleModel(p.id, m.id)} size="small" style={{ marginLeft: 4 }} />
                      </Tooltip>
                      <Tooltip title="编辑">
                        <EditOutlined style={{ fontSize: 11, cursor: 'pointer', color: '#1677ff' }} onClick={() => handleEditModel(m)} />
                      </Tooltip>
                      <Popconfirm title="删除此模型？" onConfirm={() => void handleDeleteModel(p.id, m.id)} okText="删除" cancelText="取消">
                        <DeleteOutlined style={{ fontSize: 11, cursor: 'pointer', color: '#ff4d4f' }} />
                      </Popconfirm>
                    </Tag>
                  ))}
                </div>
              )}
            </Card>
          ))}
        </div>
      )}

      {/* ── 供应商弹窗 ─────────────────────────────────── */}
      <Modal
        title={editingProvider ? '编辑供应商' : '添加供应商'}
        open={providerModalOpen}
        onCancel={() => setProviderModalOpen(false)}
        onOk={() => void handleSubmitProvider()}
        okText={editingProvider ? '保存' : '添加'}
        cancelText="取消"
        width={520}
        destroyOnClose
      >
        <Form form={providerForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="providerType" label="供应商类型">
            <Select options={PROVIDER_TYPE_OPTIONS} onChange={(v) => {
              setSelectedProviderType(v as string)
              const preset = PROVIDER_PRESETS[v as ProviderType]
              if (preset) {
                const curName = providerForm.getFieldValue('name')
                if (!curName) providerForm.setFieldsValue({ name: preset.name, baseUrl: preset.baseUrl })
              }
            }} />
          </Form.Item>
          <Form.Item name="name" label="显示名称" rules={[{ required: true, message: '请输入名称' }]}>
            <Input placeholder="如：OpenAI、Claude" />
          </Form.Item>
          <Form.Item name="baseUrl" label="API 地址" rules={[{ required: true, message: '请输入 API 地址' }]}>
            <Input placeholder="https://api.openai.com/v1" />
          </Form.Item>
          <Form.Item name="apiKey" label="API Key">
            <Input.Password placeholder="输入 API Key（Ollama 可留空）" />
          </Form.Item>
          <Form.Item name="description" label="备注">
            <Input.TextArea rows={2} placeholder="可选备注" />
          </Form.Item>
          <Space size={24}>
            <Form.Item name="isEnabled" label="启用" valuePropName="checked"><Switch /></Form.Item>
            <Form.Item name="isDefault" label="设为默认" valuePropName="checked"><Switch /></Form.Item>
          </Space>
        </Form>
      </Modal>

      {/* ── 模型弹窗 ───────────────────────────────────── */}
      <Modal
        title={editingModel ? '编辑模型' : '添加模型'}
        open={modelModalOpen}
        onCancel={() => setModelModalOpen(false)}
        onOk={() => void handleSubmitModel()}
        okText={editingModel ? '保存' : '添加'}
        cancelText="取消"
        width={520}
        destroyOnClose
      >
        <Form form={modelForm} layout="vertical" style={{ marginTop: 16 }}>
          {/* 快捷预设 */}
          {!editingModel && MODEL_PRESETS[selectedProviderType]?.length > 0 && (
            <div style={{ marginBottom: 12 }}>
              <Text type="secondary" style={{ fontSize: 12 }}>快捷选择：</Text>
              <Space size={4} style={{ marginTop: 4 }}>
                {MODEL_PRESETS[selectedProviderType].map((preset) => (
                  <Tag
                    key={preset.modelName}
                    style={{ cursor: 'pointer' }}
                    color="blue"
                    onClick={() => handlePresetSelect(preset)}
                  >
                    {preset.displayName}
                  </Tag>
                ))}
              </Space>
            </div>
          )}

          <Form.Item name="modelName" label="模型名称（调用名）" rules={[{ required: true, message: '请输入模型名' }]}>
            <Input placeholder="如 gpt-4o、qwen3.5:7b" />
          </Form.Item>
          <Form.Item name="displayName" label="显示名称">
            <Input placeholder="如 GPT-4o（留空则用模型名）" />
          </Form.Item>
          <div style={{ display: 'flex', gap: 16 }}>
            <Form.Item name="contextLength" label="上下文长度" style={{ flex: 1 }}>
              <InputNumber min={1} max={1000000} style={{ width: '100%' }} placeholder="4096" />
            </Form.Item>
            <Form.Item name="maxTokens" label="最大输出 Token" style={{ flex: 1 }}>
              <InputNumber min={1} max={128000} style={{ width: '100%' }} placeholder="4096" />
            </Form.Item>
          </div>
          <Form.Item name="temperature" label="温度 (0-2)">
            <Slider min={0} max={2} step={0.1} marks={{ 0: '精确', 1: '平衡', 2: '创意' }} />
          </Form.Item>
          <Form.Item name="remark" label="备注">
            <Input placeholder="可选备注" />
          </Form.Item>
          <Form.Item name="isEnabled" label="启用" valuePropName="checked"><Switch /></Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
