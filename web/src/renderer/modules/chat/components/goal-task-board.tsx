/**
 * Goal 模式任务看板 — 展示目标拆解的子任务及完成状态
 *
 * 仅在 Goal 模式激活时显示，位于执行进展面板上方。
 * 每个子任务完成后显示绿色勾选标记。
 */
import React from 'react'
import { Typography, Progress } from 'antd'
import {
  CheckCircleFilled,
  ClockCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined,
  AimOutlined,
} from '@ant-design/icons'
import type { GoalTask } from '../types/chat'

const { Text } = Typography

interface GoalTaskBoardProps {
  /** 子任务列表 */
  tasks: GoalTask[]
  /** 当前迭代次数 */
  iterations?: number
  /** 最大迭代次数 */
  maxIterations?: number
  /** Token 使用量 */
  tokensUsed?: number
  /** Token 预算 */
  tokenBudget?: number
}

/** 子任务状态图标 */
function TaskStatusIcon({ status }: { status: GoalTask['status'] }) {
  switch (status) {
    case 'done':
      return <CheckCircleFilled style={{ fontSize: 16, color: '#52c41a' }} />
    case 'in_progress':
      return <LoadingOutlined style={{ fontSize: 16, color: '#1677ff' }} />
    case 'failed':
      return <CloseCircleOutlined style={{ fontSize: 16, color: '#ff4d4f' }} />
    default:
      return <ClockCircleOutlined style={{ fontSize: 16, color: '#d9d9d9' }} />
  }
}

/** 子任务状态样式 */
function getTaskStyle(status: GoalTask['status']): React.CSSProperties {
  const base: React.CSSProperties = {
    display: 'flex',
    alignItems: 'flex-start',
    gap: 10,
    padding: '8px 10px',
    borderRadius: 8,
    border: '1px solid',
    transition: 'all 0.2s',
  }

  switch (status) {
    case 'done':
      return { ...base, background: '#f6ffed', borderColor: '#b7eb8f' }
    case 'in_progress':
      return { ...base, background: '#e6f4ff', borderColor: '#91caff' }
    case 'failed':
      return { ...base, background: '#fff2f0', borderColor: '#ffccc7' }
    default:
      return { ...base, background: '#fafafa', borderColor: '#f0f0f0' }
  }
}

export function GoalTaskBoard({
  tasks,
  iterations = 0,
  maxIterations = 5,
  tokensUsed = 0,
  tokenBudget = 50000,
}: GoalTaskBoardProps) {
  const hasTasks = tasks && tasks.length > 0
  const completedCount = hasTasks ? tasks.filter((t) => t.status === 'done').length : 0
  const progressPercent = hasTasks ? Math.round((completedCount / tasks.length) * 100) : 0

  return (
    <div
      style={{
        padding: '12px 14px',
        background: '#fff',
        borderRadius: 10,
        border: '1px solid #f0f0f0',
        marginBottom: 12,
      }}
    >
      {/* 标题栏 */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
        <Text strong style={{ fontSize: 13, color: '#1a1a1a', display: 'flex', alignItems: 'center', gap: 6 }}>
          <AimOutlined style={{ color: '#ff8c42' }} /> 目标任务看板
        </Text>
        {hasTasks && (
          <Text type="secondary" style={{ fontSize: 11 }}>
            {completedCount}/{tasks.length} 完成
          </Text>
        )}
      </div>

      {/* 空状态：等待任务拆解 */}
      {!hasTasks && (
        <div style={{ textAlign: 'center', padding: '16px 0', color: '#999' }}>
          <LoadingOutlined style={{ fontSize: 20, color: '#ff8c42', marginBottom: 6 }} />
          <div style={{ fontSize: 12 }}>目标模式已激活，正在规划任务...</div>
        </div>
      )}

      {/* 进度条 */}
      {hasTasks && (
        <Progress
          percent={progressPercent}
          size="small"
          status={progressPercent === 100 ? 'success' : 'active'}
          showInfo={false}
          style={{ marginBottom: 10 }}
        />
      )}

      {/* 子任务列表 */}
      {hasTasks && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {tasks.map((task) => (
            <div key={task.id} style={getTaskStyle(task.status)}>
              <TaskStatusIcon status={task.status} />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <Text
                    style={{
                      fontSize: 13,
                      fontWeight: 'normal',
                      textDecoration: task.status === 'done' ? 'line-through' : 'none',
                      color: task.status === 'done' ? '#52c41a' : task.status === 'failed' ? '#ff4d4f' : '#1a1a1a',
                    }}
                  >
                    {task.title}
                  </Text>
                  {task.progress != null && task.progress > 0 && (
                    <Text type="secondary" style={{ fontSize: 11 }}>
                      ({task.progress}%)
                    </Text>
                  )}
                </div>
                {task.dependencies && task.dependencies.length > 0 && (
                  <Text type="secondary" style={{ fontSize: 11, display: 'block', marginTop: 2 }}>
                    → 依赖: {task.dependencies.map(d => `#${d}`).join(', ')}
                  </Text>
                )}
                {task.description && (
                  <Text
                    style={{
                      fontSize: 12,
                      color: '#666',
                      display: 'block',
                      marginTop: 2,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {task.description}
                  </Text>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 底部统计 */}
      {hasTasks && (
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 10, paddingTop: 8, borderTop: '1px solid #f0f0f0' }}>
          <Text type="secondary" style={{ fontSize: 11 }}>
            迭代: {iterations}/{maxIterations}
          </Text>
          <Text type="secondary" style={{ fontSize: 11 }}>
            Token: {(tokensUsed / 1000).toFixed(1)}k/{(tokenBudget / 1000).toFixed(0)}k
          </Text>
        </div>
      )}
    </div>
  )
}
