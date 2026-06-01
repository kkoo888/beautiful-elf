/**
 * 大模型供应商配置组件
 * 支持添加/编辑/删除/启停多个 LLM 供应商
 */

import { useCallback, useEffect, useState } from 'react'
import {
  Button,
  Card,
  Form,
  Input,
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
} from '@ant-design/icons'
import {
  getProviders,
  createProvider,
  updateProvider,
  toggleProvider,
  deleteProvider,
} from '../services/settings-api'
import type {
  LLMProvider,
  LLMProviderPayload,
  ProviderType,
  LLMModelItem,
} from '../types/settings'
import { PROVIDER_PRESETS } from '../types/settings'

const { Text } = Typography

/** 供应商类型选项 */
const PROVIDER_TYPE_OPTIONS = [
  { label: 'OpenAI', value: 'openai' },
  { label: 'Claude (Anthropic)', value: 'claude' },
  { label: 'DeepSeek', value: 'deepseek' },
  { label: '通义千问', value: 'qwen' },
  { label: 'Ollama (本地)', value: 'ollama' },
  { label: '自定义', value: 'custom' },
]

/** 供应商类型对应的颜色 */
const TYPE_COLORS: Record<ProviderType, string> = {
  openai: '#10a37f',
  claude: '#d97706',
  deepseek: '#3b82f6',
  ollama: '#8b5cf6',
  qwen: '#f43f5e',
  custom: '#6b7280',
}

export function LlmProviderSettings() {
  const [providers, setProviders] = useState<LLMProvider[]>([])
  const [loading, setLoading] = useState(true)
  const [modalOpen, setModalOpen] = useState(false)
  const [editingProvider, setEditingProvider] = useState<LLMProvider | null>(null)
  const [form] = Form.useForm()

  /** 加载供应商列表 */
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

  useEffect(() => {
    void loadProviders()
  }, [loadProviders])

  /** 打开新增弹窗 */
  const handleAdd = useCallback(() => {
    setEditingProvider(null)
    form.resetFields()
    form.setFieldsValue({
      providerType: 'openai',
      isEnabled: true,
      isDefault: false,
    })
    setModalOpen(true)
  }, [form])

  /** 打开编辑弹窗 */
  const handleEdit = useCallback(
    (provider: LLMProvider) => {
      setEditingProvider(provider)
      form.setFieldsValue({
        name: provider.name,
        providerType: provider.providerType,
        baseUrl: provider.baseUrl,
        apiKey: provider.apiKey,
        description: provider.description,
        isEnabled: provider.isEnabled === 1,
        isDefault: provider.isDefault === 1,
        modelsJson: JSON.stringify(provider.models, null, 2),
      })
      setModalOpen(true)
    },
    [form]
  )

  /** 提交表单 */
  const handleSubmit = useCallback(async () => {
    try {
      const values = await form.validateFields()
      let models: LLMModelItem[] = []
      if (values.modelsJson) {
        try {
          models = JSON.parse(values.modelsJson)
        } catch {
          message.error('模型列表 JSON 格式不正确')
          return
        }
      }

      const payload: LLMProviderPayload = {
        name: values.name,
        providerType: values.providerType,
        baseUrl: values.baseUrl,
        apiKey: values.apiKey || '',
        models,
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

      setModalOpen(false)
      await loadProviders()
    } catch (e: any) {
      if (e.message) message.error(e.message)
    }
  }, [form, editingProvider, loadProviders])

  /** 切换启用状态 */
  const handleToggle = useCallback(
    async (id: number) => {
      try {
        await toggleProvider(id)
        await loadProviders()
      } catch (e: any) {
        message.error('操作失败：' + (e.message || '未知错误'))
      }
    },
    [loadProviders]
  )

  /** 删除供应商 */
  const handleDelete = useCallback(
    async (id: number) => {
      try {
        await deleteProvider(id)
        message.success('已删除')
        await loadProviders()
      } catch (e: any) {
        message.error('删除失败：' + (e.message || '未知错误'))
      }
    },
    [loadProviders]
  )

  /** 选择预设时自动填充 */
  const handleTypeChange = useCallback(
    (type: ProviderType) => {
      const preset = PROVIDER_PRESETS[type]
      if (preset) {
        form.setFieldsValue({
          name: form.getFieldValue('name') || preset.name,
          baseUrl: form.getFieldValue('baseUrl') || preset.baseUrl,
        })
      }
    },
    [form]
  )

  /** 脱敏显示 API Key */
  const maskKey = (key: string) => {
    if (!key || key.length <= 8) return '****'
    return key.slice(0, 4) + '****' + key.slice(-4)
  }

  return (
    <div>
      {/* 头部操作栏 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Text type="secondary">配置不同大模型供应商的 API 地址和密钥，启用后可在模型选择中使用</Text>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
          添加供应商
        </Button>
      </div>

      {/* 供应商列表 */}
      {providers.length === 0 && !loading ? (
        <Empty description="暂无供应商，点击上方按钮添加" style={{ padding: '48px 0' }} />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {providers.map((p) => (
            <Card
              key={p.id}
              size="small"
              style={{
                opacity: p.isEnabled ? 1 : 0.6,
                borderLeft: `3px solid ${TYPE_COLORS[p.providerType] || '#6b7280'}`,
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                {/* 左侧信息 */}
                <div style={{ flex: 1 }}>
                  <Space align="center" size={8}>
                    <CloudOutlined style={{ color: TYPE_COLORS[p.providerType], fontSize: 18 }} />
                    <Text strong style={{ fontSize: 15 }}>{p.name}</Text>
                    <Tag color={TYPE_COLORS[p.providerType]}>
                      {PROVIDER_TYPE_OPTIONS.find((o) => o.value === p.providerType)?.label || p.providerType}
                    </Tag>
                    {p.isDefault === 1 && (
                      <Tag icon={<StarFilled />} color="gold">默认</Tag>
                    )}
                    <Tag
                      icon={p.isEnabled ? <CheckCircleFilled /> : <CloseCircleFilled />}
                      color={p.isEnabled ? 'success' : 'default'}
                    >
                      {p.isEnabled ? '已启用' : '已禁用'}
                    </Tag>
                  </Space>
                  <div style={{ marginTop: 6 }}>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      <ApiOutlined /> {p.baseUrl}
                    </Text>
                  </div>
                  <div style={{ marginTop: 4 }}>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      Key: {maskKey(p.apiKey)}
                    </Text>
                    {p.models.length > 0 && (
                      <Text type="secondary" style={{ fontSize: 12, marginLeft: 12 }}>
                        模型: {p.models.map((m) => m.name).join(', ')}
                      </Text>
                    )}
                  </div>
                  {p.description && (
                    <Text type="secondary" style={{ fontSize: 12, display: 'block', marginTop: 2 }}>
                      {p.description}
                    </Text>
                  )}
                </div>

                {/* 右侧操作 */}
                <Space size={4}>
                  <Tooltip title={p.isEnabled ? '点击禁用' : '点击启用'}>
                    <Switch
                      checked={p.isEnabled === 1}
                      onChange={() => void handleToggle(p.id)}
                      size="small"
                    />
                  </Tooltip>
                  <Tooltip title="编辑">
                    <Button
                      type="text"
                      size="small"
                      icon={<EditOutlined />}
                      onClick={() => handleEdit(p)}
                    />
                  </Tooltip>
                  <Popconfirm
                    title="确定删除此供应商？"
                    onConfirm={() => void handleDelete(p.id)}
                    okText="删除"
                    cancelText="取消"
                  >
                    <Tooltip title="删除">
                      <Button type="text" size="small" danger icon={<DeleteOutlined />} />
                    </Tooltip>
                  </Popconfirm>
                </Space>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* 新增/编辑弹窗 */}
      <Modal
        title={editingProvider ? '编辑供应商' : '添加供应商'}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={() => void handleSubmit()}
        okText={editingProvider ? '保存' : '添加'}
        cancelText="取消"
        width={560}
        destroyOnClose
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="providerType" label="供应商类型">
            <Select options={PROVIDER_TYPE_OPTIONS} onChange={handleTypeChange} />
          </Form.Item>

          <Form.Item
            name="name"
            label="显示名称"
            rules={[{ required: true, message: '请输入名称' }]}
          >
            <Input placeholder="如：OpenAI、Claude、DeepSeek" />
          </Form.Item>

          <Form.Item
            name="baseUrl"
            label="API 地址"
            rules={[{ required: true, message: '请输入 API 地址' }]}
          >
            <Input placeholder="https://api.openai.com/v1" />
          </Form.Item>

          <Form.Item name="apiKey" label="API Key">
            <Input.Password placeholder="输入 API Key（可留空）" />
          </Form.Item>

          <Form.Item name="description" label="备注">
            <Input.TextArea rows={2} placeholder="可选备注信息" />
          </Form.Item>

          <Divider style={{ margin: '12px 0' }} />

          <Form.Item name="modelsJson" label="模型列表（JSON）" tooltip="手动配置该供应商下的可用模型">
            <Input.TextArea
              rows={5}
              placeholder={`[\n  { "id": "gpt-4o", "name": "GPT-4o", "contextLength": 128000, "supportsVision": true, "supportsTools": true },\n  { "id": "gpt-4o-mini", "name": "GPT-4o Mini", "contextLength": 128000 }\n]`}
              style={{ fontFamily: 'monospace', fontSize: 12 }}
            />
          </Form.Item>

          <Space size={24}>
            <Form.Item name="isEnabled" label="启用" valuePropName="checked">
              <Switch />
            </Form.Item>
            <Form.Item name="isDefault" label="设为默认" valuePropName="checked">
              <Switch />
            </Form.Item>
          </Space>
        </Form>
      </Modal>
    </div>
  )
}
