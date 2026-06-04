/**
 * 共享模型选择器组件
 * 从已启用的 LLM 供应商中选择模型
 * 支持两种用法：
 *   - 紧凑模式：单行 Select（用于专家团成员等表单内）
 *   - 完整模式：供应商 + 模型级联选择（用于聊天面板等）
 */

import { useCallback, useEffect, useMemo, useState } from 'react'
import { Select, Space, Tag, Typography } from 'antd'
import { CloudOutlined } from '@ant-design/icons'
import { getEnabledProviders } from '@/modules/settings/services/settings-api'
import type { LLMProvider, LLMModelItem } from '@/modules/settings/types/settings'

const { Text } = Typography

/** 供应商类型颜色 */
const TYPE_COLORS: Record<string, string> = {
  openai: '#10a37f',
  claude: '#d97706',
  deepseek: '#3b82f6',
  ollama: '#8b5cf6',
  qwen: '#f43f5e',
  custom: '#6b7280',
}

// ── 缓存 ─────────────────────────────────────────────────

let _cachedProviders: LLMProvider[] | null = null
let _cacheTime = 0
const CACHE_TTL = 60_000 // 1 分钟缓存

async function getProvidersCached(): Promise<LLMProvider[]> {
  const now = Date.now()
  if (_cachedProviders && now - _cacheTime < CACHE_TTL) {
    return _cachedProviders
  }
  _cachedProviders = await getEnabledProviders()
  _cacheTime = now
  return _cachedProviders
}

// ── 紧凑模式（单个 Select）──────────────────────────────────

export interface CompactModelSelectProps {
  /** 当前选中的模型全名 (providerId:modelName) */
  value?: string
  /** 选择回调 */
  onChange?: (value: string, providerId: number, modelName: string) => void
  /** 占位文本 */
  placeholder?: string
  /** 是否禁用 */
  disabled?: boolean
  /** 样式宽度 */
  style?: React.CSSProperties
}

/**
 * 紧凑模型选择器 — 单个下拉，格式 "供应商名 / 模型名"
 * value 格式: "{providerId}:{modelName}"
 */
export function CompactModelSelect({
  value,
  onChange,
  placeholder = '选择模型',
  disabled,
  style,
}: CompactModelSelectProps) {
  const [providers, setProviders] = useState<LLMProvider[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    void (async () => {
      try {
        const list = await getProvidersCached()
        setProviders(list)
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  const options = useMemo(() => {
    return providers.flatMap((p) =>
      (p.models ?? []).map((m) => ({
        label: `${p.name} / ${m.name}`,
        value: `${p.id}:${m.name}`,
        provider: p,
        model: m,
      }))
    )
  }, [providers])

  const handleChange = useCallback(
    (val: string) => {
      if (!onChange) return
      const [pid, ...rest] = val.split(':')
      onChange(val, Number(pid), rest.join(':'))
    },
    [onChange]
  )

  return (
    <Select
      value={value || undefined}
      onChange={handleChange}
      placeholder={placeholder}
      disabled={disabled}
      loading={loading}
      style={{ minWidth: 200, ...style }}
      showSearch
      optionFilterProp="label"
      options={options}
    />
  )
}

// ── 完整模式（供应商 + 模型级联）──────────────────────────────

export interface FullModelSelectProps {
  /** 当前选中的供应商 ID */
  providerId?: number
  /** 当前选中的模型名称 */
  modelName?: string
  /** 选择回调 */
  onChange?: (providerId: number, modelName: string) => void
  /** 布局方向 */
  direction?: 'horizontal' | 'vertical'
}

/**
 * 完整模型选择器 — 供应商 + 模型级联选择
 */
export function FullModelSelect({
  providerId,
  modelName,
  onChange,
  direction = 'horizontal',
}: FullModelSelectProps) {
  const [providers, setProviders] = useState<LLMProvider[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedPid, setSelectedPid] = useState<number | undefined>(providerId)

  // 同步外部 prop 变化到内部状态
  useEffect(() => {
    setSelectedPid(providerId)
  }, [providerId])

  useEffect(() => {
    void (async () => {
      try {
        const list = await getProvidersCached()
        setProviders(list)
        // 如果没选过供应商，默认选第一个（优先选默认供应商）
        if (!providerId && list.length > 0) {
          const defaultP = list.find((p) => p.isDefault === 1) ?? list[0]
          setSelectedPid(defaultP.id)
          if (onChange && defaultP.models.length > 0) {
            onChange(defaultP.id, defaultP.models[0].name)
          }
        }
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  const currentProvider = useMemo(
    () => providers.find((p) => p.id === selectedPid),
    [providers, selectedPid]
  )

  const handleProviderChange = useCallback(
    (pid: number) => {
      setSelectedPid(pid)
      const p = providers.find((x) => x.id === pid)
      if (p && p.models.length > 0 && onChange) {
        onChange(pid, p.models[0].name)
      }
    },
    [providers, onChange]
  )

  const handleModelChange = useCallback(
    (mname: string) => {
      if (selectedPid && onChange) {
        onChange(selectedPid, mname)
      }
    },
    [selectedPid, onChange]
  )

  const isHorizontal = direction === 'horizontal'

  return (
    <Space direction={isHorizontal ? 'horizontal' : 'vertical'} size={8} wrap>
      <Select
        value={selectedPid}
        onChange={handleProviderChange}
        placeholder="选择供应商"
        loading={loading}
        style={{ minWidth: 150 }}
        options={providers.map((p) => ({
          label: (
            <Space size={4}>
              <CloudOutlined style={{ color: TYPE_COLORS[p.providerType] || '#6b7280' }} />
              {p.name}
            </Space>
          ),
          value: p.id,
        }))}
      />
      <Select
        value={modelName || undefined}
        onChange={handleModelChange}
        placeholder="选择模型"
        loading={loading}
        style={{ minWidth: 180 }}
        showSearch
        optionFilterProp="label"
        options={(currentProvider?.models ?? []).map((m) => ({
          label: m.name,
          value: m.name,
        }))}
      />
    </Space>
  )
}
