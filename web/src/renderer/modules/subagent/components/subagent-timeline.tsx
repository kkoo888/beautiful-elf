/** 子代理执行步骤 Timeline */

import { Timeline, Tag, Typography, Empty } from 'antd'
import {
  CheckCircleFilled,
  CloseCircleFilled,
  LoadingOutlined,
  ClockCircleOutlined,
  MinusCircleFilled,
} from '@ant-design/icons'
import type { SubagentRun, SubagentStep, StepStatus } from '../types/subagent'
import styles from './subagent-panel.module.css'

const { Text } = Typography

const STEP_STATUS_ICON: Record<StepStatus, React.ReactNode> = {
  success: <CheckCircleFilled style={{ color: 'var(--ant-color-success)' }} />,
  failed: <CloseCircleFilled style={{ color: 'var(--ant-color-error)' }} />,
  running: <LoadingOutlined style={{ color: 'var(--ant-color-primary)' }} />,
  pending: <ClockCircleOutlined style={{ color: 'var(--ant-color-text-quaternary)' }} />,
  skipped: <MinusCircleFilled style={{ color: 'var(--ant-color-text-quaternary)' }} />,
}

const STEP_STATUS_COLOR: Record<StepStatus, string> = {
  success: 'green',
  failed: 'red',
  running: 'blue',
  pending: 'gray',
  skipped: 'gray',
}

function formatDuration(ms?: number): string {
  if (ms === undefined || ms === null) return ''
  if (ms < 1000) return `${ms}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
  return `${Math.floor(ms / 60000)}m ${Math.round((ms % 60000) / 1000)}s`
}

interface SubagentTimelineProps {
  run: SubagentRun | undefined
}

export function SubagentTimeline({ run }: SubagentTimelineProps) {
  if (!run) {
    return <Empty description="请在列表中选择一个子代理查看执行详情" />
  }

  return (
    <div className={styles.timelineContainer}>
      <div className={styles.timelineHeader}>
        <span className={styles.timelineTitle}>{run.taskName}</span>
        <Tag
          color={
            run.status === 'running'
              ? 'processing'
              : run.status === 'completed'
                ? 'success'
                : run.status === 'failed'
                  ? 'error'
                  : 'warning'
          }
        >
          {run.status === 'running'
            ? '运行中'
            : run.status === 'completed'
              ? '已完成'
              : run.status === 'failed'
                ? '失败'
                : '已终止'}
        </Tag>
      </div>
      <Timeline
        items={run.steps.map((step: SubagentStep) => ({
          icon: STEP_STATUS_ICON[step.status],
          color: STEP_STATUS_COLOR[step.status],
          content: (
            <div>
              <Text strong>{step.name}</Text>
              {step.duration !== undefined && (
                <span className={styles.elapsedTime}> · {formatDuration(step.duration)}</span>
              )}
              {step.output && <div className={styles.stepOutput}>{step.output}</div>}
              {step.error && <div className={styles.stepError}>{step.error}</div>}
            </div>
          ),
        }))}
      />
    </div>
  )
}
