/** 洞察 Tab — 借鉴 Hindsight Reflect / CARA 信念网络

功能:
  - 洞察列表（按类型筛选）
  - 手动触发反思
  - 置信度可视化
  - 洞察状态管理（active/superseded/dismissed）
*/

import { useState, useEffect, useCallback } from 'react'
import {
  Typography, Button, Space, Empty, Spin, Tag, App, Progress,
  Segmented, Popconfirm, Tooltip,
} from 'antd'
import {
  ReloadOutlined, ExperimentOutlined, DeleteOutlined,
  CheckCircleOutlined, CloseCircleOutlined,
  WarningOutlined, RiseOutlined, BulbOutlined, SyncOutlined,
} from '@ant-design/icons'
import {
  listInsights, deleteInsight, triggerReflect,
  type MemoryInsight, type ReflectResult,
} from '../services/memory-entity-api'
import memoryPanelStyles from './memory-panel.module.css'

const { Text } = Typography

const INSIGHT_TYPE_MAP: Record<string, { icon: React.ReactNode; label: string; color: string }> = {
  pattern: { icon: <SyncOutlined />, label: '模式', color: 'blue' },
  trend: { icon: <RiseOutlined />, label: '趋势', color: 'cyan' },
  risk: { icon: <WarningOutlined />, label: '风险', color: 'red' },
  insight: { icon: <BulbOutlined />, label: '洞察', color: 'orange' },
}

export function InsightTab() {
  const { message } = App.useApp()
  const [insights, setInsights] = useState<MemoryInsight[]>([])
  const [loading, setLoading] = useState(true)
  const [reflecting, setReflecting] = useState(false)
  const [typeFilter, setTypeFilter] = useState<string>('all')
  const [reflectResult, setReflectResult] = useState<ReflectResult | null>(null)

  const loadInsights = useCallback(async () => {
    setLoading(true)
    try {
      const params: any = { pageSize: 100, status: 'active' }
      if (typeFilter !== 'all') params.type = typeFilter
      const { items } = await listInsights(params)
      setInsights(items)
    } catch {} finally {
      setLoading(false)
    }
  }, [typeFilter])

  useEffect(() => { loadInsights() }, [loadInsights])

  const handleReflect = async () => {
    setReflecting(true)
    try {
      const result = await triggerReflect(7)
      setReflectResult(result)
      if (result.insights.length > 0) {
        message.success(`反思完成，发现 ${result.insights.length} 条洞察`)
        loadInsights()
      } else {
        message.info('反思完成，暂无新洞察')
      }
    } catch { message.error('反思失败') } finally { setReflecting(false) }
  }

  const handleDismiss = async (id: number) => {
    try {
      await deleteInsight(id)
      message.success('已忽略')
      setInsights(prev => prev.filter(i => i.id !== id))
    } catch { message.error('操作失败') }
  }

  const typeOptions = [
    { label: '全部', value: 'all' },
    ...Object.entries(INSIGHT_TYPE_MAP).map(([k, v]) => ({ label: v.label, value: k })),
  ]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: 12 }}>
      {/* 工具栏 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexShrink: 0 }}>
        <div className={memoryPanelStyles.memorySubmenuSegmented}>
          <Segmented
            value={typeFilter}
            onChange={v => setTypeFilter(v as string)}
            options={typeOptions}
            size="small"
          />
        </div>
        <Space size={8}>
          <Tooltip title="刷新"><Button type="text" size="small" icon={<ReloadOutlined />} onClick={loadInsights} /></Tooltip>
          <Button
            type="primary"
            size="small"
            icon={<ExperimentOutlined />}
            loading={reflecting}
            onClick={handleReflect}
          >
            反思
          </Button>
        </Space>
      </div>

      {/* 反思结果 */}
      {reflectResult && reflectResult.insights.length > 0 && (
        <div style={{
          padding: '10px 12px', background: '#f6ffed', borderRadius: 6,
          border: '1px solid #b7eb8f', fontSize: 12, flexShrink: 0,
        }}>
          <Text strong style={{ fontSize: 12 }}>最新反思结果</Text>
          <div style={{ marginTop: 4, color: '#52c41a' }}>
            分析了 {reflectResult.analyzed} 条记忆，发现 {reflectResult.insights.length} 条洞察
          </div>
        </div>
      )}

      {/* 列表 */}
      <div style={{ flex: 1, overflow: 'auto', minHeight: 0 }}>
        {loading ? (
          <div style={{ display: 'flex', justifyContent: 'center', paddingTop: 60 }}><Spin /></div>
        ) : insights.length === 0 ? (
          <Empty
            description="暂无洞察，点击「反思」从记忆中提取"
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          />
        ) : (
          <div>
            {insights.map((insight, index) => {
              const typeInfo = INSIGHT_TYPE_MAP[insight.insightType] || INSIGHT_TYPE_MAP.insight
              return (
                <div
                  key={insight.id}
                  style={{
                    padding: '12px 0',
                    borderBottom: index < insights.length - 1 ? '1px solid #f0f0f0' : 'none',
                  }}
                >
                  {/* 头部：类型 + 置信度 + 操作 */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                    <Space size={8}>
                      <Tag color={typeInfo.color} icon={typeInfo.icon} style={{ margin: 0 }}>
                        {typeInfo.label}
                      </Tag>
                      <Progress
                        percent={insight.confidence}
                        size="small"
                        style={{ width: 80 }}
                        strokeColor={insight.confidence > 70 ? '#52c41a' : insight.confidence > 40 ? '#faad14' : '#ff4d4f'}
                        format={p => `${p}%`}
                      />
                    </Space>
                    <Popconfirm title="确认忽略此洞察？" onConfirm={() => handleDismiss(insight.id)} okText="忽略" cancelText="取消">
                      <Button type="text" size="small" icon={<CloseCircleOutlined />} style={{ color: '#bfbfbf' }} />
                    </Popconfirm>
                  </div>

                  {/* 内容 */}
                  <div style={{ fontSize: 13, lineHeight: 1.7, color: '#1a1a2e' }}>
                    {insight.content}
                  </div>

                  {/* 元信息 */}
                  <div style={{ marginTop: 4, fontSize: 11, color: '#bfbfbf' }}>
                    证据 {insight.evidenceCount} 条
                    {insight.sourcePeriod && ` · ${insight.sourcePeriod}`}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
