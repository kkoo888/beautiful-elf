/**
 * 模型路由设置 — 4 个 tier 卡片（S/M/L/XL）
 * 每个卡片可选择供应商、模型、设置参数、启用/禁用
 */

import { useCallback, useEffect, useState } from 'react'
import {
  Button,
  Card,
  Form,
  InputNumber,
  Select,
  Space,
  Switch,
  Tag,
  Typography,
  message,
  Empty,
  Spin,
  Row,
  Col,
  Divider,
} from 'antd'
import {
  SaveOutlined,
  ReloadOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons'
import {
  getEnabledProviders,
  getTierConfigs,
  createTierConfig,
  updateTierConfig,
} from '../services/settings-api'
import type { LLMProvider, LLMModel } from '../types/settings'
import type { TierConfig } from '../services/settings-api'

const { Text } = Typography

const TIER_META: Record<string, { label: string; color: string; desc: string }> = {
  S: { label: 'S · 轻量', color: '#52c41a', desc: '简单闲聊、快速问答' },
  M: { label: 'M · 标准', color: '#1677ff', desc: '日常对话、知识问答' },
  L: { label: 'L · 强力', color: '#faad14', desc: '复杂分析、代码生成' },
  XL: { label: 'XL · 最强', color: '#ff4d4f', desc: '高难度推理、架构设计' },
}

const TIER_ORDER = ['S', 'M', 'L', 'XL']

export function TierRoutingSettings() {
  const [providers, setProviders] = useState<LLMProvider[]>([])
  const [tierConfigs, setTierConfigs] = useState<TierConfig[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState<string | null>(null)

  // 每个 tier 的编辑状态
  const [edits, setEdits] = useState<Record<string, {
    providerId: number
    modelName: string
    fallbackModelName: string
    temperature: number
    reasoningEnabled: boolean
    isEnabled: boolean
    configId: number | null
  }>>({})

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const [provs, configs] = await Promise.all([getEnabledProviders(), getTierConfigs()])
      setProviders(provs)
      setTierConfigs(configs)

      // 初始化 edits
      const initial: typeof edits = {}
      for (const tier of TIER_ORDER) {
        const cfg = configs.find((c) => c.tier === tier)
        if (cfg) {
          initial[tier] = {
            providerId: cfg.providerId,
            modelName: cfg.modelName,
            fallbackModelName: cfg.fallbackModelName || '',
            temperature: cfg.temperature,
            reasoningEnabled: cfg.reasoningEnabled === 1,
            isEnabled: cfg.isEnabled === 1,
            configId: cfg.id,
          }
        } else {
          initial[tier] = {
            providerId: provs[0]?.id ?? 0,
            modelName: provs[0]?.models?.[0]?.modelName ?? '',
            fallbackModelName: '',
            temperature: tier === 'S' ? 0.3 : tier === 'M' ? 0.5 : 0.7,
            reasoningEnabled: tier === 'XL',
            isEnabled: true,
            configId: null,
          }
        }
      }
      setEdits(initial)
    } catch (e: any) {
      message.error('加载失败：' + (e.message || '未知错误'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void loadData() }, [loadData])

  const handleFieldChange = useCallback((tier: string, field: string, value: any) => {
    setEdits((prev) => ({
      ...prev,
      [tier]: { ...prev[tier], [field]: value },
    }))
  }, [])

  const handleSave = useCallback(async (tier: string) => {
    const edit = edits[tier]
    if (!edit || !edit.providerId || !edit.modelName) {
      message.warning('请选择供应商和模型')
      return
    }
    setSaving(tier)
    try {
      const payload = {
        providerId: edit.providerId,
        modelName: edit.modelName,
        fallbackModelName: edit.fallbackModelName,
        temperature: edit.temperature,
        reasoningEnabled: edit.reasoningEnabled ? 1 : 0,
        isEnabled: edit.isEnabled ? 1 : 0,
      }
      if (edit.configId) {
        await updateTierConfig(edit.configId, payload)
      } else {
        const created = await createTierConfig({ tier, ...payload })
        setEdits((prev) => ({
          ...prev,
          [tier]: { ...prev[tier], configId: created.id },
        }))
      }
      message.success(`${tier} 配置已保存`)
    } catch (e: any) {
      message.error('保存失败：' + (e.message || '未知错误'))
    } finally {
      setSaving(null)
    }
  }, [edits])

  const handleSaveAll = useCallback(async () => {
    for (const tier of TIER_ORDER) {
      const edit = edits[tier]
      if (!edit || !edit.providerId || !edit.modelName) continue
      setSaving(tier)
      try {
        const payload = {
          providerId: edit.providerId,
          modelName: edit.modelName,
          fallbackModelName: edit.fallbackModelName,
          temperature: edit.temperature,
          reasoningEnabled: edit.reasoningEnabled ? 1 : 0,
          isEnabled: edit.isEnabled ? 1 : 0,
        }
        if (edit.configId) {
          await updateTierConfig(edit.configId, payload)
        } else {
          const created = await createTierConfig({ tier, ...payload })
          setEdits((prev) => ({
            ...prev,
            [tier]: { ...prev[tier], configId: created.id },
          }))
        }
      } catch {
        // 跳过失败的 tier，继续保存其他
      }
    }
    setSaving(null)
    message.success('全部保存完成')
    await loadData()
  }, [edits, loadData])

  // 获取指定供应商的模型列表
  const getModelsForProvider = useCallback((providerId: number): LLMModel[] => {
    const provider = providers.find((p) => p.id === providerId)
    return provider?.models?.filter((m) => m.isEnabled === 1) ?? []
  }, [providers])

  if (loading) {
    return <div style={{ display: 'flex', justifyContent: 'center', padding: 48 }}><Spin /></div>
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Text type="secondary">配置 ML 路由的 tier → 模型映射。Auto 模式下系统自动选择合适的 tier。</Text>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={() => void loadData()}>刷新</Button>
          <Button type="primary" icon={<SaveOutlined />} loading={!!saving} onClick={() => void handleSaveAll()}>
            全部保存
          </Button>
        </Space>
      </div>

      {providers.length === 0 ? (
        <Empty description="请先在「模型供应商」中添加供应商和模型" style={{ padding: '48px 0' }} />
      ) : (
        <Row gutter={[16, 16]}>
          {TIER_ORDER.map((tier) => {
            const meta = TIER_META[tier]
            const edit = edits[tier]
            if (!edit) return null
            const models = getModelsForProvider(edit.providerId)

            return (
              <Col xs={24} sm={12} key={tier}>
                <Card
                  size="small"
                  title={
                    <Space>
                      <ThunderboltOutlined style={{ color: meta.color }} />
                      <Tag color={meta.color} style={{ fontSize: 13, fontWeight: 600 }}>{meta.label}</Tag>
                      <Text type="secondary" style={{ fontSize: 12 }}>{meta.desc}</Text>
                    </Space>
                  }
                  extra={
                    <Switch
                      checked={edit.isEnabled}
                      onChange={(v) => handleFieldChange(tier, 'isEnabled', v)}
                      checkedChildren="启用"
                      unCheckedChildren="禁用"
                    />
                  }
                  style={{ borderLeft: `3px solid ${meta.color}` }}
                >
                  <Form layout="vertical" size="small">
                    <Form.Item label="供应商">
                      <Select
                        value={edit.providerId || undefined}
                        onChange={(v) => {
                          handleFieldChange(tier, 'providerId', v)
                          // 切换供应商时重置模型
                          const firstModel = getModelsForProvider(v)[0]
                          handleFieldChange(tier, 'modelName', firstModel?.modelName ?? '')
                        }}
                        options={providers.map((p) => ({
                          label: p.name,
                          value: p.id,
                        }))}
                        placeholder="选择供应商"
                      />
                    </Form.Item>
                    <Form.Item label="模型">
                      <Select
                        value={edit.modelName || undefined}
                        onChange={(v) => handleFieldChange(tier, 'modelName', v)}
                        options={models.map((m) => ({
                          label: m.displayName || m.modelName,
                          value: m.modelName,
                        }))}
                        placeholder="选择模型"
                        showSearch
                        optionFilterProp="label"
                      />
                    </Form.Item>
                    <Form.Item label="降级模型（可选）">
                      <Select
                        value={edit.fallbackModelName || undefined}
                        onChange={(v) => handleFieldChange(tier, 'fallbackModelName', v || '')}
                        allowClear
                        options={models
                          .filter((m) => m.modelName !== edit.modelName)
                          .map((m) => ({
                            label: m.displayName || m.modelName,
                            value: m.modelName,
                          }))}
                        placeholder="主模型不可用时降级"
                      />
                    </Form.Item>
                    <Space size={12}>
                      <Form.Item label="Temperature">
                        <InputNumber
                          min={0}
                          max={2}
                          step={0.1}
                          value={edit.temperature}
                          onChange={(v) => handleFieldChange(tier, 'temperature', v ?? 0.7)}
                          style={{ width: 90 }}
                        />
                      </Form.Item>
                    </Space>
                    <Form.Item label="Extended Thinking" style={{ marginBottom: 8 }}>
                      <Switch
                        checked={edit.reasoningEnabled}
                        onChange={(v) => handleFieldChange(tier, 'reasoningEnabled', v)}
                        checkedChildren="开"
                        unCheckedChildren="关"
                      />
                    </Form.Item>
                  </Form>
                  <Divider style={{ margin: '8px 0 12px' }} />
                  <Button
                    type="primary"
                    size="small"
                    icon={<SaveOutlined />}
                    loading={saving === tier}
                    onClick={() => void handleSave(tier)}
                    block
                  >
                    保存 {tier} 配置
                  </Button>
                </Card>
              </Col>
            )
          })}
        </Row>
      )}
    </div>
  )
}
