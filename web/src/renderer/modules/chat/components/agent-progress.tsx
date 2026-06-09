/**
 * Agent 执行进展指示器 — 展示 Agent 每一步的执行状态
 *
 * 基于 AG-UI 协议 STEP_STARTED/STEP_FINISHED 模式。
 * 配合 LangGraph get_stream_writer() custom stream mode 使用。
 */
import { Typography } from 'antd'
import {
  CheckCircleOutlined,
  LoadingOutlined,
  CloseCircleOutlined,
  MinusCircleOutlined,
} from '@ant-design/icons'
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
