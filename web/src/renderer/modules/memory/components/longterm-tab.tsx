/** 长期记忆 Tab — MEMORY.md 编辑 + 提炼记忆卡片（Hindsight 借鉴）

设计原则（frontend-design skill）:
  - 不用 Modal（用 Drawer）
  - 不嵌套 Card（扁平列表 + 分割线）
  - 按钮层级分明（ghost / primary）
  - 不重复信息
  - 空状态引导操作
  - 颜色对齐项目设计系统（主色 #E8913A）
  - 渐进展开（来源日志带动画）
 */

import { useState, useEffect, useCallback } from 'react'
import {
  Typography, Button, Spin, App, Space, Empty, Tag, Tooltip,
  Drawer, Form, InputNumber, Checkbox, Input, Popconfirm,
  Segmented, Steps,
} from 'antd'
import {
  EditOutlined, SaveOutlined, BookOutlined,
  ExperimentOutlined, DeleteOutlined, ReloadOutlined,
  LinkOutlined, FileTextOutlined, BulbOutlined,
  CaretDownOutlined, CaretRightOutlined,
} from '@ant-design/icons'
import {
  fetchLongTermMemory, updateLongTermMemory,
  distillMemories, listObservations, deleteObservation,
} from '../services/memory-api'
import type {
  MarkdownMemoryEntry, DistillRequest, Observation,
} from '../services/memory-api'
import { MemoryGraphTab } from './memory-graph-tab'
import { EntityTab } from './entity-tab'
import { InsightTab } from './insight-tab'

const { Text } = Typography
const { TextArea } = Input

// ── 设计常量（对齐项目 Design Token）──────────────────────

const COLORS = {
  primary: '#E8913A',
  primaryBg: '#FFF7ED',
  primaryBorder: '#FDBA74',
  info: '#3BA0E8',
  textSecondary: '#8C8C8C',
  textTertiary: '#BFBFBF',
  border: '#F0F0F0',
  bgHover: '#FAFAFA',
  bgTag: '#F5F5F5',
}

const CATEGORY_OPTIONS = [
  { label: '🔑 决策', value: 'decisions' },
  { label: '🐛 踩坑', value: 'pitfalls' },
  { label: '👤 偏好', value: 'preferences' },
  { label: '📦 状态', value: 'status' },
]

const CATEGORY_MAP: Record<string, { icon: string; color: string; bg: string }> = {
  decisions: { icon: '🔑', color: '#1677FF', bg: '#E6F4FF' },
  pitfalls: { icon: '🐛', color: '#FF4D4F', bg: '#FFF2F0' },
  preferences: { icon: '👤', color: '#722ED1', bg: '#F9F0FF' },
  status: { icon: '📦', color: '#52C41A', bg: '#F6FFED' },
}

const FRESHNESS_MAP: Record<string, { label: string; color: string }> = {
  new: { label: '新', color: '#1677FF' },
  stable: { label: '稳定', color: '#52C41A' },
  strengthening: { label: '增强中', color: '#E8913A' },
  weakening: { label: '减弱中', color: '#FAAD14' },
  stale: { label: '过期', color: '#BFBFBF' },
}

const DEFAULT_MISSION = '提取技术决策、架构选型、踩坑经验、主人偏好。忽略寒暄和临时调试信息。'

// ── 主组件 ────────────────────────────────────────────────

export function LongTermTab() {
  const { message } = App.useApp()
  const [memory, setMemory] = useState<MarkdownMemoryEntry | null>(null)
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState(false)
  const [editContent, setEditContent] = useState('')
  const [saving, setSaving] = useState(false)

  const [viewMode, setViewMode] = useState<'observations' | 'entities' | 'insights' | 'memory' | 'graph'>('observations')
  const [observations, setObservations] = useState<Observation[]>([])
  const [obsLoading, setObsLoading] = useState(false)
  const [categoryFilter, setCategoryFilter] = useState<string>('all')
  const [categoryCounts, setCategoryCounts] = useState<Record<string, number>>({})

  const [drawerOpen, setDrawerOpen] = useState(false)
  const [distillStep, setDistillStep] = useState(-1) // -1=未开始, 0=读取, 1=提炼, 2=写入, 3=完成
  const [distilling, setDistilling] = useState(false)
  const [distillDays, setDistillDays] = useState(7)
  const [distillMission, setDistillMission] = useState(DEFAULT_MISSION)
  const [distillDirectives, setDistillDirectives] = useState('')
  const [distillCategories, setDistillCategories] = useState<string[]>(
    CATEGORY_OPTIONS.map(c => c.value)
  )

  // ── 初始化 ────────────────────────────────────────────

  useEffect(() => {
    fetchLongTermMemory()
      .then(setMemory)
      .catch(() => {})
      .finally(() => setLoading(false))
    loadObservations()
    loadCounts()
  }, [])

  const loadObservations = useCallback(async (category?: string) => {
    setObsLoading(true)
    try {
      const cat = category && category !== 'all' ? category : undefined
      const { items } = await listObservations({ category: cat, pageSize: 100 })
      setObservations(items)
    } catch {} finally {
      setObsLoading(false)
    }
  }, [])

  const loadCounts = useCallback(async () => {
    try {
      // 从 observations 推算分类计数
      const { items } = await listObservations({ pageSize: 1000 })
      const counts: Record<string, number> = {}
      items.forEach(o => { counts[o.category] = (counts[o.category] || 0) + 1 })
      setCategoryCounts(counts)
    } catch {}
  }, [])

  // ── MEMORY.md 操作 ────────────────────────────────────

  const handleEdit = useCallback(() => {
    setEditContent(memory?.content ?? '')
    setEditing(true)
  }, [memory])

  const handleSave = useCallback(async () => {
    setSaving(true)
    try {
      const updated = await updateLongTermMemory(editContent)
      setMemory(updated)
      setEditing(false)
      message.success('已保存')
    } catch { message.error('保存失败') } finally { setSaving(false) }
  }, [editContent])

  // ── 提炼操作 ──────────────────────────────────────────

  const handleDistill = useCallback(async () => {
    setDistilling(true)
    setDistillStep(0)
    try {
      // 模拟步骤进度（实际是单次 API 调用）
      const timer0 = setTimeout(() => setDistillStep(1), 800)
      const timer1 = setTimeout(() => setDistillStep(2), 3000)

      const request: DistillRequest = {
        days: distillDays,
        mission: distillMission,
        directives: distillDirectives.split('\n').filter(d => d.trim()),
        categories: distillCategories,
      }
      const result = await distillMemories(request)

      clearTimeout(timer0)
      clearTimeout(timer1)
      setDistillStep(3)
      message.success(`提炼完成，共 ${result.totalCount} 条记忆`)

      // 延迟关闭 drawer，让用户看到完成状态
      setTimeout(() => {
        setDrawerOpen(false)
        setDistillStep(-1)
        loadObservations(categoryFilter)
        loadCounts()
      }, 1200)
    } catch (err: any) {
      message.error(err?.response?.data?.message || '提炼失败')
      setDistillStep(-1)
    } finally {
      setDistilling(false)
    }
  }, [distillDays, distillMission, distillDirectives, distillCategories, categoryFilter])

  const handleCategoryFilter = useCallback((value: string) => {
    setCategoryFilter(value)
    loadObservations(value)
  }, [loadObservations])

  const handleDeleteObs = useCallback(async (id: number) => {
    const target = observations.find(o => o.id === id)
    setObservations(prev => prev.filter(o => o.id !== id))
    message.info({
      content: '已删除',
      duration: 3,
      key: `delete-${id}`,
    })
    try {
      await deleteObservation(id)
      loadCounts()
    } catch {
      // 回滚
      if (target) setObservations(prev => [...prev, target])
      message.error('删除失败')
    }
  }, [observations])

  // ── Loading ───────────────────────────────────────────

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
        <Spin />
      </div>
    )
  }

  // ── 分类筛选选项（带计数）────────────────────────────

  const filterOptions = [
    { label: `全部 (${observations.length})`, value: 'all' },
    ...CATEGORY_OPTIONS.map(opt => ({
      label: `${opt.label} (${categoryCounts[opt.value] || 0})`,
      value: opt.value,
    })),
  ]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: 16 }}>
      {/* ── 顶部工具栏 ── */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexShrink: 0 }}>
        <Segmented
          value={viewMode}
          onChange={v => setViewMode(v as typeof viewMode)}
          options={[
            { label: '提炼记忆', value: 'observations' },
            { label: '实体', value: 'entities' },
            { label: '洞察', value: 'insights' },
            { label: '关系图', value: 'graph' },
            { label: 'MEMORY.md', value: 'memory' },
          ]}
        />
        {viewMode === 'observations' && (
          <Space size={8}>
            <Tooltip title="刷新列表">
              <Button
                type="text"
                size="small"
                icon={<ReloadOutlined />}
                onClick={() => { loadObservations(categoryFilter); loadCounts() }}
              />
            </Tooltip>
            <Button
              type="primary"
              size="small"
              icon={<ExperimentOutlined />}
              onClick={() => setDrawerOpen(true)}
            >
              提炼记忆
            </Button>
          </Space>
        )}
      </div>

      {/* ── 提炼记忆视图 ── */}
      {viewMode === 'observations' && (
        <div style={{ flex: 1, overflow: 'auto', minHeight: 0 }}>
          {/* 分类筛选 */}
          <Segmented
            value={categoryFilter}
            onChange={v => handleCategoryFilter(v as string)}
            options={filterOptions}
            size="small"
            style={{ marginBottom: 16 }}
          />

          {/* 列表 */}
          {obsLoading ? (
            <div style={{ display: 'flex', justifyContent: 'center', paddingTop: 60 }}>
              <Spin />
            </div>
          ) : observations.length === 0 ? (
            <EmptyState onDistill={() => setDrawerOpen(true)} />
          ) : (
            <div>
              {observations.map((obs, index) => (
                <ObservationItem
                  key={obs.id}
                  obs={obs}
                  onDelete={handleDeleteObs}
                  isLast={index === observations.length - 1}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── 实体视图 ── */}
      {viewMode === 'entities' && (
        <div style={{ flex: 1, minHeight: 0 }}>
          <EntityTab />
        </div>
      )}

      {/* ── 洞察视图 ── */}
      {viewMode === 'insights' && (
        <div style={{ flex: 1, minHeight: 0 }}>
          <InsightTab />
        </div>
      )}

      {/* ── 关系图视图 ── */}
      {viewMode === 'graph' && (
        <div style={{ flex: 1, minHeight: 0, position: 'relative' }}>
          <MemoryGraphTab />
        </div>
      )}

      {/* ── MEMORY.md 视图 ── */}
      {viewMode === 'memory' && memory && (
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12, flexShrink: 0 }}>
            <Space size={8}>
              <BookOutlined style={{ color: COLORS.primary }} />
              <Text strong>长期记忆</Text>
              <Text type="secondary" style={{ fontSize: 12 }}>{memory.wordCount} 字</Text>
            </Space>
            {editing ? (
              <Space size={8}>
                <Button size="small" onClick={() => setEditing(false)}>取消</Button>
                <Button size="small" type="primary" icon={<SaveOutlined />} loading={saving} onClick={handleSave}>保存</Button>
              </Space>
            ) : (
              <Button size="small" type="text" icon={<EditOutlined />} onClick={handleEdit}>编辑</Button>
            )}
          </div>

          <div style={{ flex: 1, overflow: 'auto', minHeight: 0 }}>
            {editing ? (
              <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
                <Text type="secondary" style={{ marginBottom: 8, fontSize: 12 }}>支持 Markdown 格式</Text>
                <textarea
                  value={editContent}
                  onChange={e => setEditContent(e.target.value)}
                  style={{
                    flex: 1, minHeight: 300, padding: 16,
                    border: `1px solid ${COLORS.border}`, borderRadius: 8,
                    fontFamily: "'SFMono-Regular', Consolas, 'PingFang SC', sans-serif",
                    fontSize: 13, lineHeight: 1.8, resize: 'vertical',
                    background: 'transparent',
                  }}
                />
              </div>
            ) : (
              <div
                style={{ whiteSpace: 'pre-wrap', lineHeight: 1.8, fontSize: 14 }}
                dangerouslySetInnerHTML={{ __html: renderMarkdown(memory.content) }}
              />
            )}
          </div>
        </div>
      )}

      {/* ── 提炼配置 Drawer ── */}
      <Drawer
        title={
          <Space size={8}>
            <ExperimentOutlined style={{ color: COLORS.primary }} />
            <span>提炼记忆</span>
          </Space>
       }
        open={drawerOpen}
        onClose={() => { if (!distilling) { setDrawerOpen(false); setDistillStep(-1) } }}
        size="default"
        destroyOnHidden
        extra={
          distillStep < 0 ? (
            <Button type="primary" icon={<ExperimentOutlined />} loading={distilling} onClick={handleDistill}>
              开始提炼
            </Button>
          ) : null
        }
      >
        {distillStep >= 0 ? (
          /* ── 提炼进度 ── */
          <div style={{ padding: '24px 0' }}>
            <Steps
              current={distillStep}
              orientation="vertical"
              size="small"
              items={[
                { title: '读取日志', content: `最近 ${distillDays} 天的 daily log` },
                { title: 'AI 提炼', content: '调用 LLM 结构化提取' },
                { title: '写入记忆', content: '保存到提炼记忆列表' },
                { title: '完成', content: '提炼成功！' },
              ]}
            />
          </div>
        ) : (
          /* ── 配置表单 ── */
          <Form layout="vertical" size="small">
            <Form.Item label="提取天数">
              <InputNumber
                min={1} max={30} value={distillDays}
                onChange={v => setDistillDays(v ?? 7)}
                style={{ width: 120 }}
              />
            </Form.Item>
            <Form.Item label="提炼指令（Mission）">
              <TextArea
                rows={2} value={distillMission}
                onChange={e => setDistillMission(e.target.value)}
                style={{ fontSize: 13 }}
              />
            </Form.Item>
            <Form.Item label="硬规则（Directives，每行一条）">
              <TextArea
                rows={2} value={distillDirectives}
                onChange={e => setDistillDirectives(e.target.value)}
                placeholder="例如：必须标注来源日期&#10;忽略临时调试信息"
                style={{ fontSize: 13 }}
              />
            </Form.Item>
            <Form.Item label="提炼分类">
              <Checkbox.Group
                options={CATEGORY_OPTIONS}
                value={distillCategories}
                onChange={v => setDistillCategories(v as string[])}
              />
            </Form.Item>
          </Form>
        )}
      </Drawer>
    </div>
  )
}

// ── 空状态组件 ────────────────────────────────────────────

function EmptyState({ onDistill }: { onDistill: () => void }) {
  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      justifyContent: 'center', padding: '48px 24px', textAlign: 'center',
    }}>
      <div style={{
        width: 64, height: 64, borderRadius: 16,
        background: COLORS.primaryBg, display: 'flex',
        alignItems: 'center', justifyContent: 'center',
        marginBottom: 16,
      }}>
        <BulbOutlined style={{ fontSize: 28, color: COLORS.primary }} />
      </div>
      <Text strong style={{ fontSize: 16, marginBottom: 8 }}>还没有提炼记忆</Text>
      <Text type="secondary" style={{ fontSize: 13, marginBottom: 24, maxWidth: 280 }}>
        从每日日志中提炼关键决策、踩坑经验和偏好，让 AI 记住重要的事
      </Text>
      <Button type="primary" icon={<ExperimentOutlined />} onClick={onDistill}>
        开始提炼
      </Button>
    </div>
  )
}

// ── 提炼记忆条目组件（扁平设计，不嵌套 Card）─────────────

function ObservationItem({ obs, onDelete, isLast }: {
  obs: Observation; onDelete: (id: number) => void; isLast: boolean
}) {
  const [expanded, setExpanded] = useState(false)
  const cat = CATEGORY_MAP[obs.category] ?? { icon: '📌', color: '#8C8C8C', bg: COLORS.bgTag }
  const fresh = FRESHNESS_MAP[obs.freshness] ?? { label: obs.freshness, color: '#8C8C8C' }

  return (
    <div style={{
      padding: '14px 0',
      borderBottom: isLast ? 'none' : `1px solid ${COLORS.border}`,
    }}>
      {/* 头部行：分类 + 新鲜度 + 证据数 + 删除 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <Space size={6} wrap={false}>
          <span style={{
            display: 'inline-flex', alignItems: 'center', gap: 4,
            padding: '1px 8px', borderRadius: 4,
            background: cat.bg, color: cat.color, fontSize: 12, fontWeight: 500,
          }}>
            {cat.icon} {CATEGORY_OPTIONS.find(c => c.value === obs.category)?.label?.split(' ')[1] || obs.category}
          </span>
          <Text style={{ fontSize: 12, color: fresh.color }}>
            {fresh.label}
          </Text>
          {obs.proofCount > 0 && (
            <Tooltip title={`${obs.proofCount} 条来源日志`}>
              <Text type="secondary" style={{ fontSize: 12 }}>
                <LinkOutlined style={{ marginRight: 2 }} />{obs.proofCount}
              </Text>
            </Tooltip>
          )}
        </Space>
        <Popconfirm
          title="确认删除这条提炼记忆？"
          onConfirm={() => onDelete(obs.id)}
          okText="删除"
          cancelText="取消"
          placement="left"
        >
          <Button type="text" size="small" icon={<DeleteOutlined />} style={{ color: COLORS.textTertiary }} />
        </Popconfirm>
      </div>

      {/* 内容 */}
      <div
        style={{ whiteSpace: 'pre-wrap', lineHeight: 1.7, fontSize: 13, color: '#262626' }}
        dangerouslySetInnerHTML={{ __html: renderMarkdown(obs.content) }}
      />

      {/* 来源日志（可展开，带动画） */}
      {obs.sources && obs.sources.length > 0 && (
        <div style={{ marginTop: 8 }}>
          <button
            onClick={() => setExpanded(!expanded)}
            style={{
              display: 'inline-flex', alignItems: 'center', gap: 4,
              background: 'none', border: 'none', cursor: 'pointer',
              padding: '2px 0', fontSize: 12, color: COLORS.info,
            }}
          >
            {expanded ? <CaretDownOutlined /> : <CaretRightOutlined />}
            <FileTextOutlined />
            来源日志 ({obs.sources.length})
          </button>

          <div style={{
            overflow: 'hidden',
            maxHeight: expanded ? `${obs.sources.length * 60 + 16}px` : '0',
            opacity: expanded ? 1 : 0,
            transition: 'max-height 0.3s ease-out, opacity 0.2s ease-out',
            marginTop: expanded ? 8 : 0,
          }}>
            <div style={{
              paddingLeft: 12, borderLeft: `2px solid ${COLORS.border}`,
            }}>
              {obs.sources.map(src => (
                <div key={src.sourceId} style={{ marginBottom: 8 }}>
                  <Text style={{ fontSize: 12, color: COLORS.textSecondary }}>
                    {src.logTitle}
                  </Text>
                  {src.evidenceQuote && (
                    <div style={{
                      fontSize: 12, color: '#595959', fontStyle: 'italic',
                      paddingLeft: 8, marginTop: 2,
                      borderLeft: `2px solid ${COLORS.primaryBorder}`,
                      lineHeight: 1.6,
                    }}>
                      "{src.evidenceQuote}"
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Markdown 渲染 ────────────────────────────────────────

function renderMarkdown(md: string): string {
  return md
    .replace(/^### (.+)$/gm, '<h4 style="margin:12px 0 6px;font-size:14px;font-weight:600;color:#262626;">$1</h4>')
    .replace(/^## (.+)$/gm, '<h3 style="margin:16px 0 8px;font-size:15px;font-weight:600;color:#262626;border-bottom:1px solid #f0f0f0;padding-bottom:4px;">$1</h3>')
    .replace(/^# (.+)$/gm, '<h2 style="margin:20px 0 10px;font-size:16px;font-weight:700;color:#262626;">$1</h2>')
    .replace(/^> (.+)$/gm, '<blockquote style="border-left:3px solid #E8913A;padding-left:10px;color:#595959;margin:8px 0;font-style:italic;">$1</blockquote>')
    .replace(/^- (.+)$/gm, '<div style="display:flex;gap:6px;margin:3px 0;"><span style="color:#E8913A;flex-shrink:0;">•</span><span>$1</span></div>')
    .replace(/\*\*(.+?)\*\*/g, '<strong style="font-weight:600;">$1</strong>')
    .replace(/`([^`]+)`/g, '<code style="background:#f5f5f5;padding:1px 4px;border-radius:3px;font-size:12px;font-family:SFMono-Regular,Consolas,monospace;">$1</code>')
    .replace(/\n{2,}/g, '</p><p style="margin:6px 0;">')
    .replace(/\n/g, '<br/>')
    .replace(/^/, '<p style="margin:6px 0;">')
    .replace(/$/, '</p>')
}
