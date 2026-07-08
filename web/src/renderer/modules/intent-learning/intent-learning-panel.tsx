import { useMemo, useState } from 'react'
import { Tabs, Table, Tag, Card, Button, Empty, Spin, Badge, App, Alert } from 'antd'
import {
  HistoryOutlined,
  NodeIndexOutlined,
  BulbOutlined,
  CheckOutlined,
  CloseOutlined,
  ThunderboltOutlined,
  BranchesOutlined,
  PlayCircleOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import 'dayjs/locale/zh-cn'
import { PageHeader } from '@/components/page-header'
import {
  useIntentCorrections,
  useBehaviorPatterns,
  useSkillSuggestions,
  useAnalyzeBehavior,
  useCreateIntentFromPattern,
} from './hooks/use-intent-learning'
import type { IntentCorrection, BehaviorPattern, SkillSuggestion, AnalyzeResult } from './types/intent-learning'
import styles from './intent-learning-panel.module.css'

dayjs.extend(relativeTime)
dayjs.locale('zh-cn')

// ── 统计概览 ─────────────────────────────────────────────

function StatsOverview({
  corrections,
  patterns,
  suggestions,
}: {
  corrections: number
  patterns: number
  suggestions: number
}) {
  return (
    <div className={styles.statsRow}>
      <div className={styles.statCard}>
        <div className={styles.statIcon}>📝</div>
        <div className={styles.statValue}>{corrections}</div>
        <div className={styles.statLabel}>纠正记录</div>
      </div>
      <div className={styles.statCard}>
        <div className={styles.statIcon}>🔗</div>
        <div className={styles.statValue}>{patterns}</div>
        <div className={styles.statLabel}>行为模式</div>
      </div>
      <div className={styles.statCard}>
        <div className={styles.statIcon}>💡</div>
        <div className={styles.statValue}>{suggestions}</div>
        <div className={styles.statLabel}>待处理建议</div>
      </div>
    </div>
  )
}

// ── 分析结果展示 ─────────────────────────────────────────

function AnalysisResultCard({ result }: { result: AnalyzeResult | null }) {
  if (!result) return null
  if (!result.purpose && !result.thoughts) return null

  return (
    <Alert
      type="info"
      showIcon
      style={{ marginBottom: 16 }}
      message="🧠 LLM 分析过程"
      description={
        <div style={{ fontSize: 13, lineHeight: 1.8 }}>
          {result.purpose && (
            <div><strong>Purpose:</strong> {result.purpose}</div>
          )}
          {result.thoughts && (
            <div><strong>Thoughts:</strong> {result.thoughts}</div>
          )}
        </div>
      }
    />
  )
}

// ── 纠正历史表格 ─────────────────────────────────────────

const correctionColumns = [
  {
    title: '原始意图',
    dataIndex: 'originalIntent',
    key: 'originalIntent',
    render: (text: string) => <span className={styles.intentText}>{text}</span>,
  },
  {
    title: '纠正为',
    dataIndex: 'correctModule',
    key: 'correctModule',
    width: 120,
    render: (module: string) => <Tag color="blue">{module}</Tag>,
  },
  {
    title: '时间',
    dataIndex: 'createdAt',
    key: 'createdAt',
    width: 140,
    render: (time: string) => (
      <span style={{ color: 'rgba(0,0,0,0.35)', fontSize: 12 }}>{dayjs(time).fromNow()}</span>
    ),
  },
]

function CorrectionHistory() {
  const { data: corrections = [], isLoading } = useIntentCorrections()

  if (isLoading) return <Spin style={{ display: 'block', margin: '40px auto' }} />

  return (
    <Table<IntentCorrection>
      columns={correctionColumns}
      dataSource={corrections}
      rowKey="id"
      loading={isLoading}
      pagination={{ pageSize: 10, showSizeChanger: false }}
      size="middle"
      className={styles.correctionTable}
      locale={{ emptyText: <Empty description="暂无纠正记录" /> }}
    />
  )
}

// ── 行为模式展示 ─────────────────────────────────────────

function PatternDisplay() {
  const { data: patterns = [], isLoading } = useBehaviorPatterns()
  const createIntentMutation = useCreateIntentFromPattern()

  const handleCreateIntent = async (patternId: string) => {
    try {
      const result = await createIntentMutation.mutateAsync(patternId)
      message.success(`意图创建成功: ${result.intentName}`)
    } catch (e: any) {
      message.error(e.message || '创建失败')
    }
  }

  if (isLoading) return <Spin style={{ display: 'block', margin: '40px auto' }} />

  if (patterns.length === 0) {
    return (
      <div className={styles.emptyState}>
        <BranchesOutlined className={styles.emptyIcon} />
        <div className={styles.emptyText}>暂无行为模式<br />系统会自动学习你的使用习惯</div>
      </div>
    )
  }

  return (
    <div>
      {patterns.map((pattern) => (
        <Card key={pattern.id} size="small" className={styles.patternCard}>
          <div className={styles.patternHeader}>
            <p className={styles.patternDesc}>{pattern.description}</p>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              {pattern.isSolved === 1 && (
                <Tag color="success" icon={<CheckCircleOutlined />}>已解决</Tag>
              )}
              <Badge
                count={`${pattern.frequency} 次`}
                style={{
                  backgroundColor: '#f0f5ff',
                  color: '#1677ff',
                  border: '1px solid #d6e4ff',
                  fontWeight: 600,
                }}
              />
            </div>
          </div>
          <div className={styles.actionFlow}>
            {pattern.actions.map((action, index) => (
              <span key={index}>
                <Tag className={styles.actionTag}>{action}</Tag>
                {index < pattern.actions.length - 1 && (
                  <span className={styles.actionArrow}>→</span>
                )}
              </span>
            ))}
          </div>
          {pattern.isSolved !== 1 && pattern.frequency >= 10 && (
            <div style={{ marginTop: 12 }}>
              <Button
                size="small"
                type="dashed"
                onClick={() => handleCreateIntent(pattern.id)}
                loading={createIntentMutation.isPending}
              >
                创建意图
              </Button>
            </div>
          )}
        </Card>
      ))}
    </div>
  )
}

// ── 技能建议展示 ─────────────────────────────────────────

function SkillSuggestionList() {
  const { data: suggestions = [], isLoading, acceptSuggestion, ignoreSuggestion } =
    useSkillSuggestions()

  if (isLoading) return <Spin style={{ display: 'block', margin: '40px auto' }} />

  if (suggestions.length === 0) {
    return (
      <div className={styles.emptyState}>
        <ThunderboltOutlined className={styles.emptyIcon} />
        <div className={styles.emptyText}>暂无待处理建议<br />系统会根据行为模式自动生成技能建议</div>
      </div>
    )
  }

  return (
    <div>
      {suggestions.map((suggestion) => (
        <Card key={suggestion.id} size="small" className={styles.suggestionCard}>
          <div className={styles.suggestionHeader}>
            <div style={{ flex: 1 }}>
              <p className={styles.suggestionName}>{suggestion.name}</p>
              <p className={styles.suggestionDesc}>{suggestion.description}</p>
              <div className={styles.suggestionMeta}>
                <span>🕐 {dayjs(suggestion.createdAt).fromNow()}</span>
                {suggestion.ignoreCount > 0 && (
                  <span style={{ color: '#ff4d4f' }}>已忽略 {suggestion.ignoreCount} 次</span>
                )}
                {suggestion.lastFeedback && (
                  <span>最近反馈: {suggestion.lastFeedback === 'accepted' ? '✅ 已接受' : '❌ 已忽略'}</span>
                )}
              </div>
            </div>
            <div className={styles.suggestionActions}>
              <Button
                type="primary"
                size="small"
                icon={<CheckOutlined />}
                onClick={() => acceptSuggestion(suggestion.id)}
              >
                创建技能
              </Button>
              <Button
                size="small"
                icon={<CloseOutlined />}
                onClick={() => ignoreSuggestion(suggestion.id)}
              >
                忽略
              </Button>
            </div>
          </div>
        </Card>
      ))}
    </div>
  )
}

// ── 主面板 ───────────────────────────────────────────────

export default function IntentLearningPanel() {
  const { message } = App.useApp()
  const { data: corrections = [] } = useIntentCorrections()
  const { data: patterns = [] } = useBehaviorPatterns()
  const { data: suggestions = [] } = useSkillSuggestions()
  const analyzeMutation = useAnalyzeBehavior()
  const [analyzeResult, setAnalyzeResult] = useState<AnalyzeResult | null>(null)

  const pendingSuggestions = useMemo(
    () => suggestions.length,
    [suggestions]
  )

  const handleAnalyze = async () => {
    try {
      const result = await analyzeMutation.mutateAsync()
      setAnalyzeResult(result)
      const msg = `分析完成: 发现 ${result.patternsFound} 个模式, ${result.patternsNew} 个新增, ${result.suggestionsNew} 个新建议`
      message.success(msg)
    } catch (e: any) {
      message.error(e.message || '分析失败')
    }
  }

  const tabItems = [
    {
      key: 'corrections',
      label: (
        <span>
          <HistoryOutlined /> 纠正历史
        </span>
      ),
      children: <CorrectionHistory />,
    },
    {
      key: 'patterns',
      label: (
        <span>
          <NodeIndexOutlined /> 行为模式
        </span>
      ),
      children: <PatternDisplay />,
    },
    {
      key: 'suggestions',
      label: (
        <span>
          <BulbOutlined /> 技能建议
        </span>
      ),
      children: <SkillSuggestionList />,
    },
  ]

  return (
    <div className={styles.panel}>
      <PageHeader
        title="🧠 意图学习"
        description="系统自动学习你的使用习惯，优化意图识别和技能推荐"
        extra={
          <Button
            type="primary"
            icon={<PlayCircleOutlined />}
            loading={analyzeMutation.isPending}
            onClick={handleAnalyze}
          >
            {analyzeMutation.isPending ? '分析中...' : '分析行为模式'}
          </Button>
        }
      />

      <StatsOverview
        corrections={corrections.length}
        patterns={patterns.length}
        suggestions={pendingSuggestions}
      />

      <AnalysisResultCard result={analyzeResult} />

      <div className={styles.tabContent}>
        <Tabs items={tabItems} defaultActiveKey="corrections" />
      </div>
    </div>
  )
}
