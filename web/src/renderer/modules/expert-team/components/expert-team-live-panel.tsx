/**
 * 专家团实时执行面板
 *
 * 展示专家团执行过程中的实时状态：
 * - 专家状态卡片（谁在工作、谁完成了）
 * - 思考链/推理过程展示
 * - 任务进度
 */

import { Card, Tag, Space, Typography, Timeline, Progress, Empty, Collapse, Avatar } from 'antd'
import {
  LoadingOutlined,
  CheckCircleFilled,
  CloseCircleFilled,
  RobotOutlined,
  BulbOutlined,
} from '@ant-design/icons'
import { useState, useEffect, useMemo, useCallback } from 'react'
import { useWSMessage } from '@/services/websocket'
import type {
  ExpertStatusEvent,
  ExpertThinkingEvent,
  ExpertProgressEvent,
  LiveExpertState,
  LiveExecutionState,
} from '../types'

const { Text, Paragraph } = Typography

interface ExpertTeamLivePanelProps {
  /** 当前选中的专家团 ID（用于过滤 WebSocket 事件） */
  teamId?: number
  /** 外部触发的运行 ID */
  runId?: number
  /** 最大轮次 */
  maxRounds?: number
  /** 执行完成回调 */
  onComplete?: (output: string) => void
}

/** 专家角色颜色映射 */
const ROLE_COLORS: Record<string, string> = {
  Orchestrator: '#1890ff',
  Synthesizer: '#722ed1',
  '架构师': '#1890ff',
  '测试专家': '#52c41a',
  '产品经理': '#faad14',
  '设计师': '#eb2f96',
  '安全专家': '#f5222d',
  '创意总监': '#1890ff',
  '创意策划师': '#faad14',
  '图文创作专家': '#52c41a',
}

function getRoleColor(role: string): string {
  return ROLE_COLORS[role] || '#8c8c8c'
}

/** 专家状态卡片 */
function ExpertCard({ expert }: { expert: LiveExpertState }) {
  const statusIcon = {
    idle: <ClockIcon />,
    running: <LoadingOutlined style={{ color: '#1890ff' }} />,
    done: <CheckCircleFilled style={{ color: '#52c41a' }} />,
    failed: <CloseCircleFilled style={{ color: '#f5222d' }} />,
  }

  const statusLabel = {
    idle: '待命',
    running: '分析中...',
    done: '已完成',
    failed: '失败',
  }

  const statusColor = {
    idle: 'default',
    running: 'processing',
    done: 'success',
    failed: 'error',
  }

  return (
    <Card
      size="small"
      style={{
        borderLeft: `3px solid ${getRoleColor(expert.role)}`,
        opacity: expert.status === 'idle' ? 0.5 : 1,
      }}
      styles={{ body: { padding: '8px 12px' } }}
    >
      <Space orientation="vertical" size={4} style={{ width: '100%' }}>
        <Space>
          <Avatar
            size="small"
            style={{ backgroundColor: getRoleColor(expert.role) }}
          >
            {expert.avatar || expert.name[0]}
          </Avatar>
          <Text strong>{expert.name}</Text>
          <Tag color={getRoleColor(expert.role)} style={{ margin: 0 }}>
            {expert.role}
          </Tag>
          <Tag color={statusColor[expert.status]} icon={statusIcon[expert.status]} style={{ margin: 0 }}>
            {statusLabel[expert.status]}
          </Tag>
        </Space>
        {expert.status === 'running' && expert.thinking && (
          <Text
            type="secondary"
            style={{ fontSize: 12, lineHeight: '16px' }}
            ellipsis={{ tooltip: true }}
          >
            {expert.thinking.slice(0, 80)}...
          </Text>
        )}
        {expert.status === 'done' && expert.durationMs > 0 && (
          <Text type="secondary" style={{ fontSize: 12 }}>
            耗时 {(expert.durationMs / 1000).toFixed(1)}s
          </Text>
        )}
      </Space>
    </Card>
  )
}

/** 时钟图标组件 */
function ClockIcon() {
  return (
    <span style={{ color: '#8c8c8c', fontSize: 12 }}>⏰</span>
  )
}

/** 主面板 */
export function ExpertTeamLivePanel({
  teamId,
  runId: externalRunId,
  maxRounds = 3,
  onComplete,
}: ExpertTeamLivePanelProps) {
  const [state, setState] = useState<LiveExecutionState>({
    runId: null,
    status: 'idle',
    currentRound: 0,
    maxRounds,
    experts: new Map(),
    thinkingLog: [],
    output: '',
  })

  // 更新专家状态
  const handleExpertStatus = useCallback((msg: { payload: Record<string, unknown> }) => {
    const event = msg.payload as unknown as ExpertStatusEvent
    if (teamId && event.teamId && event.teamId !== teamId) return

    setState((prev) => {
      const next = { ...prev }
      const key = `${event.expertName}-${event.expertRole}`
      const existing = next.experts.get(key)

      if (event.status === 'running') {
        // 编排器开始 → 整体进入编排阶段
        if (event.expertRole === 'Orchestrator') {
          next.status = 'orchestrating'
          next.runId = event.runId
        }
        // 汇总器开始 → 进入汇总阶段
        if (event.expertRole === 'Synthesizer') {
          next.status = 'synthesizing'
        }
        // 普通专家开始 → 进入讨论阶段
        if (event.expertRole !== 'Orchestrator' && event.expertRole !== 'Synthesizer') {
          next.status = 'discussing'
        }
        next.currentRound = event.round
      }

      if (event.status === 'done') {
        // 汇总器完成 → 整体完成
        if (event.expertRole === 'Synthesizer') {
          next.status = 'completed'
        }
      }

      if (event.status === 'failed') {
        if (event.expertRole === 'Synthesizer') {
          next.status = 'failed'
        }
      }

      // 更新专家状态
      const newExperts = new Map(next.experts)
      newExperts.set(key, {
        name: event.expertName,
        role: event.expertRole,
        avatar: event.avatar || existing?.avatar || '🤖',
        status: event.status,
        currentRound: event.round,
        thinking: existing?.thinking || '',
        durationMs: event.durationMs || existing?.durationMs || 0,
      })
      next.experts = newExperts

      return next
    })
  }, [teamId])

  // 更新推理内容
  const handleExpertThinking = useCallback((msg: { payload: Record<string, unknown> }) => {
    const event = msg.payload as unknown as ExpertThinkingEvent
    if (teamId && event.teamId && event.teamId !== teamId) return

    setState((prev) => {
      const next = { ...prev }
      const key = `${event.expertName}-${event.expertRole}`
      const existing = next.experts.get(key)

      // 更新专家思考内容（不改变状态，thinking 事件在专家运行中就会发送）
      const newExperts = new Map(next.experts)
      newExperts.set(key, {
        name: event.expertName,
        role: event.expertRole,
        avatar: event.avatar || existing?.avatar || '🤖',
        status: existing?.status || 'running', // 保持当前状态，不强制设为 done
        currentRound: event.round,
        thinking: event.content,
        durationMs: event.durationMs || existing?.durationMs || 0,
      })
      next.experts = newExperts

      // 添加到思考日志
      next.thinkingLog = [...prev.thinkingLog, event]

      return next
    })
  }, [teamId])

  // 更新进度
  const handleExpertProgress = useCallback((msg: { payload: Record<string, unknown> }) => {
    const event = msg.payload as unknown as ExpertProgressEvent
    if (teamId && event.teamId && event.teamId !== teamId) return

    setState((prev) => ({
      ...prev,
      status: event.status === 'completed' ? 'completed' : event.status === 'failed' ? 'failed' : prev.status,
      output: event.output || prev.output,
    }))

    if (event.status === 'completed' && event.output) {
      onComplete?.(event.output)
    }
  }, [teamId, onComplete])

  // 订阅 WebSocket 事件
  useWSMessage('expert_status', handleExpertStatus)
  useWSMessage('expert_thinking', handleExpertThinking)
  useWSMessage('expert_progress', handleExpertProgress)

  // 外部 runId 变化时重置状态
  useEffect(() => {
    if (externalRunId && externalRunId !== state.runId) {
      setState({
        runId: externalRunId,
        status: 'orchestrating',
        currentRound: 0,
        maxRounds,
        experts: new Map(),
        thinkingLog: [],
        output: '',
      })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [externalRunId, maxRounds])

  // 计算进度百分比
  const progressPercent = useMemo(() => {
    if (state.status === 'completed') return 100
    if (state.status === 'idle') return 0
    if (state.status === 'orchestrating') return 5
    if (state.status === 'synthesizing') return 90
    // 讨论阶段：根据轮次计算
    const roundProgress = (state.currentRound / state.maxRounds) * 80
    return 10 + roundProgress
  }, [state.status, state.currentRound, state.maxRounds])

  const statusLabel = {
    idle: '等待执行',
    orchestrating: '🎯 编排器分析任务...',
    discussing: `💬 专家讨论中 (第 ${state.currentRound} 轮)`,
    synthesizing: '📋 汇总器生成报告...',
    completed: '✅ 执行完成',
    failed: '❌ 执行失败',
  }

  if (state.status === 'idle' && state.experts.size === 0) {
    return (
      <Card title="📡 实时执行状态" size="small">
        <Empty
          description="执行专家团后，这里会实时显示专家工作状态和推理过程"
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        />
      </Card>
    )
  }

  return (
    <Card
      title={
        <Space>
          <span>📡 实时执行状态</span>
          {state.runId && <Tag>Run #{state.runId}</Tag>}
        </Space>
      }
      size="small"
      extra={
        <Tag
          color={
            state.status === 'completed'
              ? 'success'
              : state.status === 'failed'
                ? 'error'
                : 'processing'
          }
        >
          {statusLabel[state.status]}
        </Tag>
      }
    >
      {/* 进度条 */}
      <Progress
        percent={progressPercent}
        status={
          state.status === 'completed'
            ? 'success'
            : state.status === 'failed'
              ? 'exception'
              : 'active'
        }
        showInfo={false}
        style={{ marginBottom: 16 }}
      />

      {/* 专家状态卡片 */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))',
          gap: 8,
          marginBottom: 16,
        }}
      >
        {Array.from(state.experts.values()).map((expert) => (
          <ExpertCard key={`${expert.name}-${expert.role}`} expert={expert} />
        ))}
      </div>

      {/* 思考链/推理过程 */}
      {state.thinkingLog.length > 0 && (
        <Collapse
          size="small"
          defaultActiveKey={['thinking']}
          items={[
            {
              key: 'thinking',
              label: (
                <Space>
                  <BulbOutlined />
                  <span>推理过程</span>
                  <Tag>{state.thinkingLog.length} 条记录</Tag>
                </Space>
              ),
              children: (
                <Timeline
                  items={state.thinkingLog.map((event) => ({
                    color: getRoleColor(event.expertRole),
                    children: (
                      <div>
                        <Space>
                          <Avatar
                            size="small"
                            style={{ backgroundColor: getRoleColor(event.expertRole) }}
                          >
                            {event.avatar || event.expertName[0]}
                          </Avatar>
                          <Text strong>{event.expertName}</Text>
                          <Tag color={getRoleColor(event.expertRole)} style={{ margin: 0 }}>
                            {event.expertRole}
                          </Tag>
                          {event.round > 0 && (
                            <Tag style={{ margin: 0 }}>第 {event.round} 轮</Tag>
                          )}
                          {event.durationMs && event.durationMs > 0 && (
                            <Text type="secondary" style={{ fontSize: 12 }}>
                              {(event.durationMs / 1000).toFixed(1)}s
                            </Text>
                          )}
                        </Space>
                        <Paragraph
                          style={{
                            marginTop: 4,
                            whiteSpace: 'pre-wrap',
                            maxHeight: 200,
                            overflow: 'auto',
                            fontSize: 13,
                          }}
                        >
                          {event.content}
                        </Paragraph>
                      </div>
                    ),
                  }))}
                />
              ),
            },
          ]}
        />
      )}
    </Card>
  )
}
