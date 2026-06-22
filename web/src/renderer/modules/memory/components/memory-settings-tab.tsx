/** 记忆设置 Tab — 配置记忆任务使用的 LLM 模型 */

import { useState, useCallback, useEffect } from 'react'
import { Typography, Select, Space, Spin, App, Tag, Button } from 'antd'
import { SaveOutlined, ReloadOutlined } from '@ant-design/icons'
import {
  fetchMemoryModelSetting, updateMemoryModelSetting, fetchMemoryModelOptions,
} from '../services/memory-api'
import type { MemoryModelOption } from '../services/memory-api'

const { Text } = Typography

export function MemorySettingsTab() {
  const { message } = App.useApp()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [selectedKey, setSelectedKey] = useState<string>('')
  const [models, setModels] = useState<MemoryModelOption[]>([])

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const [settings, availableModels] = await Promise.all([
        fetchMemoryModelSetting(),
        fetchMemoryModelOptions(),
      ])
      if (settings.providerId && settings.modelName) {
        setSelectedKey(`${settings.providerId}:${settings.modelName}`)
      }
      setModels(availableModels)
    } catch {
      message.error('加载设置失败')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadData() }, [loadData])

  const handleSave = useCallback(async () => {
    if (!selectedKey) {
      message.warning('请先选择一个模型')
      return
    }
    const [providerIdStr, modelName] = selectedKey.split(':')
    const providerId = parseInt(providerIdStr, 10)
    if (!providerId || !modelName) {
      message.warning('选择格式错误')
      return
    }
    setSaving(true)
    try {
      await updateMemoryModelSetting(providerId, modelName)
      message.success('设置已保存')
    } catch {
      message.error('保存失败')
    } finally {
      setSaving(false)
    }
  }, [selectedKey])

  const selectOptions = models.map(m => ({
    value: `${m.providerId}:${m.modelName}`,
    label: (
      <Space>
        <Text strong>{m.displayName || m.modelName}</Text>
        <Text type="secondary" style={{ fontSize: 12 }}>{m.providerName}</Text>
      </Space>
    ),
  }))

  const currentModelInfo = models.find(m => `${m.providerId}:${m.modelName}` === selectedKey)

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', paddingTop: 80 }}>
        <Spin />
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20, padding: '8px 0' }}>
      <Text type="secondary">
        配置记忆模块定时任务（提炼、整理、衰减等）使用的 LLM 模型。更改后下次任务执行时生效。
      </Text>

      {/* 模型选择 */}
      <div style={{
        padding: '20px 24px',
        borderRadius: 12,
        background: 'linear-gradient(135deg, rgba(255,247,237,0.6) 0%, rgba(255,241,224,0.4) 100%)',
        border: '1px solid rgba(232,145,58,0.2)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
          <Space>
            <Text strong style={{ fontSize: 14 }}>记忆任务模型</Text>
            {currentModelInfo && (
              <Tag color="orange">{currentModelInfo.displayName || currentModelInfo.modelName}</Tag>
            )}
          </Space>
          <Button
            type="text"
            icon={<ReloadOutlined />}
            onClick={loadData}
            loading={loading}
          >
            刷新
          </Button>
        </div>

        <div style={{ marginBottom: 12 }}>
          <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 6 }}>
            从已启用的供应商中选择模型
          </Text>
          <Select
            value={selectedKey || undefined}
            onChange={setSelectedKey}
            placeholder="选择模型..."
            style={{ width: '100%' }}
            options={selectOptions}
            showSearch
            filterOption={(input, option) =>
              String(option?.label?.props?.children?.[0] ?? option?.value ?? '').toLowerCase().includes(input.toLowerCase())
            }
            notFoundContent={models.length === 0 ? '暂无可用模型，请先在「供应商管理」中启用模型' : '无匹配结果'}
          />
        </div>

        {currentModelInfo && (
          <div style={{
            padding: '8px 12px',
            background: '#fff',
            borderRadius: 8,
            border: '1px solid #f0f0f0',
            fontSize: 12,
            color: '#8c8c8c',
          }}>
            供应商: <Text strong>{currentModelInfo.providerName}</Text> | 模型: <Text code>{currentModelInfo.modelName}</Text>
          </div>
        )}

        {!selectedKey && models.length > 0 && (
          <div style={{
            padding: '8px 12px',
            background: '#fff7e6',
            borderRadius: 8,
            border: '1px solid #ffe58f',
            fontSize: 12,
            color: '#ad6800',
          }}>
            尚未选择模型，记忆任务将使用默认配置 (qwen3.5:7b)
          </div>
        )}

        <div style={{ marginTop: 16, display: 'flex', justifyContent: 'flex-end' }}>
          <Button
            type="primary"
            icon={<SaveOutlined />}
            onClick={handleSave}
            loading={saving}
          >
            保存设置
          </Button>
        </div>
      </div>
    </div>
  )
}
