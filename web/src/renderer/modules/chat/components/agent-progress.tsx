/**
 * Agent 执行进展指示器 — 展示 Agent 每一步的执行状态
 *
 * 基于 AG-UI 协议 STEP_STARTED/STEP_FINISHED 模式。
 * 配合 LangGraph get_stream_writer() custom stream mode 使用。
 *
 * v2.0: 专家团步骤渲染丰富卡片（头像、角色、轮次）
 */
import { Typography, Progress, Tag } from 'antd'
import {
  CheckCircleOutlined,
  LoadingOutlined,
  CloseCircleOutlined,
  MinusCircleOutlined,
} from '@ant-design/icons'
import { ExpertAvatar } from '@/components/expert-avatar'
import type { ProgressStep } from '../../types/chat'

const { Text } = Typography

interface AgentProgressIndicatorProps {
  /** 进展步骤列表 */
  steps: ProgressStep[]
}

/** 步骤图标映射 */
const STEP_ICONS: Record<string, string> = {
  intent: '🎯',
  tools: '🔧',
  rewrite: '✏️',
  context: '📦',
  llm: '🤖',
  skill: '⚡',
  eval: '📊',
  memory_save: '💾',
  expert_team: '🧠',
  pm_plan: '📋',
  pm_eval: '📝',
  pm_report: '📄',
}

/** 是否为进行中状态 */
function isActive(status: ProgressStep['status']): boolean {
  return ['searching', 'executing', 'calling', 'checking', 'saving'].includes(status)
}

/** 状态图标 */
function StatusIcon({ status }: { status: ProgressStep['status'] }) {
  if (isActive(status)) {
    return <LoadingOutlined style={{ fontSize: 13, color: '#1677ff' }} />
  }
  if (status === 'done') {
    return <CheckCircleOutlined style={{ fontSize: 13, color: '#52c41a' }} />
  }
  if (status === 'error') {
    return <CloseCircleOutlined style={{ fontSize: 13, color: '#ff4d4f' }} />
  }
  return <MinusCircleOutlined style={{ fontSize: 13, color: '#bfbfbf' }} />
}

/** 判断是否为专家团相关步骤 */
function isExpertStep(step: ProgressStep): boolean {
  return !!(step.step?.startsWith('expert_') || step.step === 'pm_plan' || step.step === 'pm_eval' || step.step === 'pm_report')
}

/** 渲染专家团丰富卡片 */
function ExpertCard({ step }: { step: ProgressStep }) {
  const name = (step.expertName as string) || ''
  const role = (step.expertRole as string) || ''
  const avatar = (step.avatar as string) || '🤖'
  const round = step.round as number | undefined
  const maxRounds = step.maxRounds as number | undefined

  const isRunning = isActive(step.status)
  const isDone = step.status === 'done'
  const isError = step.status === 'error'

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'flex-start',
        gap: 10,
        padding: '8px 10px',
        background: isRunning ? '#e6f4ff' : isError ? '#fff2f0' : '#f6ffed',
        borderRadius: 8,
        border: `1px solid ${isRunning ? '#91caff' : isError ? '#ffccc7' : '#b7eb8f'}`,
      }}
    >
      {/* 头像（统一组件：emoji / base64 / URL 自动处理）*/}
      <ExpertAvatar avatar={avatar} size={28} bgColor={isRunning ? '#bae0ff' : isError ? '#ffccc7' : '#d9f7be'} />

      {/* 内容 */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
          <Text strong style={{ fontSize: 13 }}>{name}</Text>
          {role && <Tag style={{ fontSize: 11, lineHeight: '18px', padding: '0 4px', margin: 0 }}>{role}</Tag>}
          {round != null && maxRounds != null && maxRounds > 1 && (
            <Tag color="blue" style={{ fontSize: 11, lineHeight: '18px', padding: '0 4px', margin: 0 }}>
              第 {round}/{maxRounds} 轮
            </Tag>
          )}
          <StatusIcon status={step.status} />
        </div>

        {/* 子任务或消息 */}
        {step.message && (
          <Text style={{ fontSize: 12, color: '#666', display: 'block', marginTop: 2 }}>
            {step.message}
          </Text>
        )}

        {/* 进行中：显示进度条 */}
        {isRunning && (
          <Progress
            percent={100}
            size="small"
            status="active"
            showInfo={false}
            style={{ margin: '4px 0 0' }}
          />
        )}
      </div>

      {/* 耗时 */}
      {step.elapsedMs != null && step.elapsedMs > 0 && (
        <Text type="secondary" style={{ fontSize: 11, flexShrink: 0 }}>
          {(step.elapsedMs / 1000).toFixed(1)}s
        </Text>
      )}
    </div>
  )
}

export function AgentProgressIndicator({ steps }: AgentProgressIndicatorProps) {
  if (!steps || steps.length === 0) return null

  return (
    <div
      style={{
        padding: '10px 14px',
        margin: '8px 0',
        background: '#fafafa',
        borderRadius: 10,
        border: '1px solid #f0f0f0',
      }}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {steps.map((step) => {
          // 专家团步骤 → 丰富卡片
          if (isExpertStep(step)) {
            return <ExpertCard key={step.step} step={step} />
          }

          // 普通步骤 → 简洁行
          const icon = STEP_ICONS[step.step] ?? '▶️'
          return (
            <div
              key={step.step}
              style={{ display: 'flex', alignItems: 'center', gap: 8 }}
            >
              <StatusIcon status={step.status} />
              <Text style={{ fontSize: 13, flex: 1 }}>
                {icon} {step.message}
              </Text>
              {step.elapsedMs != null && step.elapsedMs > 0 && (
                <Text type="secondary" style={{ fontSize: 11 }}>
                  {(step.elapsedMs / 1000).toFixed(1)}s
                </Text>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
