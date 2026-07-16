import { useEffect, useState, useCallback } from 'react'
import { Card, Form, InputNumber, Switch, Button, Space, Tooltip, Typography, Divider, App, Skeleton } from 'antd'
import {
  SaveOutlined,
  ReloadOutlined,
  SettingOutlined,
  InfoCircleOutlined,
  BlockOutlined,
  SearchOutlined,
  SortAscendingOutlined,
  ApiOutlined,
} from '@ant-design/icons'
import { apiClient } from '@/services/api-client'
import { KNOWLEDGE_ENDPOINTS } from '@/services/endpoints'

const { Text } = Typography

/** RAG 配置类型 */
interface RagConfig {
  chunkSize: number
  chunkOverlap: number
  similarityTopK: number
  bm25TopN: number
  rrfK: number
  rerankEnabled: boolean
  rerankTopN: number
  embeddingModel: string
  embeddingDimension: number
  queryRewriteEnabled: boolean
}

/** 默认配置 */
const DEFAULT_CONFIG: RagConfig = {
  chunkSize: 2048,
  chunkOverlap: 256,
  similarityTopK: 10,
  bm25TopN: 20,
  rrfK: 60,
  rerankEnabled: true,
  rerankTopN: 5,
  embeddingModel: '',
  embeddingDimension: 1024,
  queryRewriteEnabled: true,
}

/** 配置项定义 */
interface ConfigField {
  key: keyof RagConfig
  label: string
  tip: string
  type: 'number' | 'switch'
  min?: number
  max?: number
  step?: number
  unit?: string
  group: 'chunk' | 'retrieval' | 'rerank' | 'embedding' | 'query'
}

const CONFIG_FIELDS: ConfigField[] = [
  // 分块参数
  { key: 'chunkSize', label: '分块大小', tip: '每个文本块的 token 数量。越大保留上下文越多，但检索精度可能下降', type: 'number', min: 128, max: 8192, step: 128, unit: 'tokens', group: 'chunk' },
  { key: 'chunkOverlap', label: '分块重叠', tip: '相邻块重叠的 token 数，防止语义在边界处断裂', type: 'number', min: 0, max: 2048, step: 64, unit: 'tokens', group: 'chunk' },

  // 检索参数
  { key: 'similarityTopK', label: '向量检索数', tip: '语义向量检索返回的最大条数', type: 'number', min: 1, max: 50, group: 'retrieval' },
  { key: 'bm25TopN', label: '关键词检索数', tip: 'BM25 全文检索返回的最大条数', type: 'number', min: 1, max: 100, group: 'retrieval' },
  { key: 'rrfK', label: 'RRF 融合 k', tip: 'Reciprocal Rank Fusion 参数，越大越平滑', type: 'number', min: 1, max: 200, group: 'retrieval' },

  // 重排序参数
  { key: 'rerankEnabled', label: '启用重排序', tip: '使用 Cross-Encoder 对检索结果精排，提升精度', type: 'switch', group: 'rerank' },
  { key: 'rerankTopN', label: '重排序保留数', tip: '精排后保留的条数', type: 'number', min: 1, max: 20, group: 'rerank' },

  // Embedding 参数
  { key: 'embeddingDimension', label: '向量维度', tip: 'Embedding 模型输出的向量维度', type: 'number', min: 64, max: 4096, step: 64, group: 'embedding' },

  // 查询改写
  { key: 'queryRewriteEnabled', label: '启用查询改写', tip: '将口语化查询改写为精确检索查询，提升召回率', type: 'switch', group: 'query' },
]

/** 分组配置 */
const GROUPS = [
  { key: 'chunk', label: '分块策略', icon: <BlockOutlined />, desc: '控制文档如何被切分为文本块' },
  { key: 'retrieval', label: '检索策略', icon: <SearchOutlined />, desc: '控制如何从知识库中检索相关内容' },
  { key: 'rerank', label: '重排序', icon: <SortAscendingOutlined />, desc: '对检索结果精排，提升最终质量' },
  { key: 'embedding', label: '向量模型', icon: <ApiOutlined />, desc: '文本转向量的模型参数' },
  { key: 'query', label: '查询优化', icon: <SearchOutlined />, desc: '优化用户查询以提升检索效果' },
]

export function RagSettings() {
  const { message } = App.useApp()
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [config, setConfig] = useState<RagConfig>(DEFAULT_CONFIG)

  /** 加载配置 */
  const loadConfig = useCallback(async () => {
    setLoading(true)
    try {
      const resp = await apiClient.get(KNOWLEDGE_ENDPOINTS.RAG_CONFIG)
      const data = (resp as any)?.data?.data || (resp as any)?.data || DEFAULT_CONFIG
      setConfig(data)
      form.setFieldsValue(data)
    } catch {
      message.warning('加载配置失败，使用默认值')
      setConfig(DEFAULT_CONFIG)
      form.setFieldsValue(DEFAULT_CONFIG)
    } finally {
      setLoading(false)
    }
  }, [form])

  /** 保存配置 */
  const handleSave = useCallback(async () => {
    setSaving(true)
    try {
      const values = await form.validateFields()
      await apiClient.put(KNOWLEDGE_ENDPOINTS.RAG_CONFIG, values)
      message.success('RAG 配置已保存')
      setConfig(values)
    } catch {
      message.error('保存失败')
    } finally {
      setSaving(false)
    }
  }, [form])

  /** 重置为当前值 */
  const handleReset = useCallback(() => {
    form.setFieldsValue(config)
    message.info('已重置为当前配置')
  }, [form, config])

  useEffect(() => { loadConfig() }, [loadConfig])

  if (loading) {
    return (
      <div style={{ padding: '24px 0' }}>
        <Skeleton active paragraph={{ rows: 8 }} />
      </div>
    )
  }

  return (
    <div style={{ padding: '0 0 24px' }}>
      {/* 操作栏 */}
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        marginBottom: 24, padding: '12px 0',
      }}>
        <Text type="secondary" style={{ fontSize: 13 }}>
          调整 RAG 检索管道参数，优化知识库检索效果
        </Text>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={handleReset}>重置</Button>
          <Button type="primary" icon={<SaveOutlined />} loading={saving} onClick={handleSave}>
            保存配置
          </Button>
        </Space>
      </div>

      <Form form={form} layout="vertical" initialValues={config}>
        {GROUPS.map((group) => {
          const fields = CONFIG_FIELDS.filter((f) => f.group === group.key)
          if (!fields.length) return null

          return (
            <Card
              key={group.key}
              style={{ marginBottom: 16, borderRadius: 8 }}
              styles={{ body: { padding: '16px 24px' } }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                <span style={{ fontSize: 16, color: '#1677ff' }}>{group.icon}</span>
                <Text strong style={{ fontSize: 15 }}>{group.label}</Text>
              </div>
              <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 16 }}>
                {group.desc}
              </Text>
              <Divider style={{ margin: '0 0 16px' }} />

              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
                gap: '12px 24px',
              }}>
                {fields.map((field) => (
                  <div key={field.key} style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    {field.type === 'switch' ? (
                      <Form.Item name={field.key} valuePropName="checked" style={{ marginBottom: 0, flex: 1 }}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                          <Space size={4}>
                            <Text>{field.label}</Text>
                            <Tooltip title={field.tip}>
                              <InfoCircleOutlined style={{ color: '#999', fontSize: 12 }} />
                            </Tooltip>
                          </Space>
                          <Switch size="small" />
                        </div>
                      </Form.Item>
                    ) : (
                      <Form.Item name={field.key} style={{ marginBottom: 0, flex: 1 }}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                          <Space size={4}>
                            <Text style={{ whiteSpace: 'nowrap' }}>{field.label}</Text>
                            <Tooltip title={field.tip}>
                              <InfoCircleOutlined style={{ color: '#999', fontSize: 12 }} />
                            </Tooltip>
                          </Space>
                          <InputNumber
                            min={field.min}
                            max={field.max}
                            step={field.step || 1}
                            size="small"
                            style={{ width: 100 }}
                            addonAfter={field.unit ? <span style={{ fontSize: 10, color: '#999' }}>{field.unit}</span> : undefined}
                          />
                        </div>
                      </Form.Item>
                    )}
                  </div>
                ))}
              </div>
            </Card>
          )
        })}
      </Form>
    </div>
  )
}
