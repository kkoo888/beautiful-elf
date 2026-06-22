/**
 * Goal 模式任务看板 — 展示目标拆解的子任务、完成状态、关联工具调用
 *
 * 设计原则：
 * - 每个子任务是可折叠的卡片，展开后显示关联的工具调用
 * - 进行中的子任务自动展开，已完成/待定的默认折叠
 * - 工具调用实时更新状态（running/done/error）
 * - 底部显示迭代次数和 Token 消耗
 */
import React, { useState, useMemo } from 'react'
import { Typography, Progress, Collapse, Tooltip, Tag } from 'antd'
import {
  CheckCircleFilled,
  ClockCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined,
  AimOutlined,
  CaretRightOutlined,
  ToolOutlined,
  PauseCircleOutlined,
} from '@ant-design/icons'
import type { GoalTask, ToolProgress } from '../types/chat'

const { Text } = Typography

interface GoalTaskBoardProps {
  tasks: GoalTask[]
  iterations?: number
  maxIterations?: number
  tokensUsed?: number
  tokenBudget?: number
}

/** 工具中文名映射 */
const TOOL_LABELS: Record<string, string> = {
  search_knowledge: '📚 搜索知识库',
  search_memory: '🧠 搜索记忆',
  web_search: '🌐 网络搜索',
  mimo_web_search: '🔍 搜索',
  execute_code: '💻 执行代码',
  read_file: '📄 读取文件',
  write_file: '✏️ 写入文件',
  edit: '✏️ 编辑文件',
  read: '📄 读取',
  api_call: '🔗 API 调用',
  database_query: '🗄️ 数据库查询',
  skill_view: '⚡ 查看技能',
  skill_manage: '⚡ 管理技能',
}

/** 子任务状态图标 */
function TaskStatusIcon({ status }: { status: GoalTask['status'] }) {
  switch (status) {
    case 'done':
      return <CheckCircleFilled style={{ fontSize: 15, color: '#52c41a' }} />
    case 'in_progress':
      return <LoadingOutlined style={{ fontSize: 15, color: '#1677ff' }} />
    case 'failed':
      return <CloseCircleOutlined style={{ fontSize: 15, color: '#ff4d4f' }} />
    case 'blocked':
      return <PauseCircleOutlined style={{ fontSize: 15, color: '#faad14' }} />
    default:
      return <ClockCircleOutlined style={{ fontSize: 15, color: '#d9d9d9' }} />
  }
}

/** 工具状态图标 */
function ToolStatusIcon({ status }: { status: ToolProgress['status'] }) {
  if (status === 'running') {
    return <LoadingOutlined style={{ fontSize: 12, color: '#1677ff' }} />
  }
  if (status === 'error') {
    return <CloseCircleOutlined style={{ fontSize: 12, color: '#ff4d4f' }} />
  }
  return <CheckCircleFilled style={{ fontSize: 12, color: '#52c41a' }} />
}

/** 子任务卡片样式 */
function getTaskCardStyle(status: GoalTask['status'], isActive: boolean): React.CSSProperties {
  const base: React.CSSProperties = {
    borderRadius: 8,
    border: '1px solid',
    overflow: 'hidden',
    transition: 'all 0.2s ease',
  }

  if (isActive) {
    return { ...base, background: '#f0f7ff', borderColor: '#91caff', boxShadow: '0 0 0 1px rgba(22,119,255,0.08)' }
  }
  switch (status) {
    case 'done':
      return { ...base, background: '#f9fff9', borderColor: '#d9f7be' }
    case 'failed':
      return { ...base, background: '#fff8f6', borderColor: '#ffccc7' }
    case 'blocked':
      return { ...base, background: '#fffbe6', borderColor: '#ffe58f' }
    default:
      return { ...base, background: '#fafafa', borderColor: '#f0f0f0' }
  }
}

/** 状态标签 */
function StatusTag({ status }: { status: GoalTask['status'] }) {
  switch (status) {
    case 'done':
      return <Tag color="success" style={{ fontSize: 10, lineHeight: '16px', padding: '0 4px', margin: 0 }}>完成</Tag>
    case 'in_progress':
      return <Tag color="processing" style={{ fontSize: 10, lineHeight: '16px', padding: '0 4px', margin: 0 }}>执行中</Tag>
    case 'failed':
      return <Tag color="error" style={{ fontSize: 10, lineHeight: '16px', padding: '0 4px', margin: 0 }}>失败</Tag>
    case 'blocked':
      return <Tag color="warning" style={{ fontSize: 10, lineHeight: '16px', padding: '0 4px', margin: 0 }}>等待</Tag>
    default:
      return <Tag style={{ fontSize: 10, lineHeight: '16px', padding: '0 4px', margin: 0, color: '#999' }}>待定</Tag>
  }
}

/** 单个工具调用行 */
function ToolRow({ tool }: { tool: ToolProgress }) {
  const label = TOOL_LABELS[tool.tool] ?? tool.tool
  const isRunning = tool.status === 'running'
  const duration = tool.startTime && !isRunning ? Date.now() - tool.startTime : 0

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 6,
        padding: '3px 0',
        fontSize: 12,
      }}
    >
      <ToolStatusIcon status={tool.status} />
      <Text style={{ flex: 1, fontSize: 12, color: tool.status === 'error' ? '#ff4d4f' : '#444' }}>
        {label}
      </Text>
      {isRunning ? (
        <Tag color="processing" style={{ fontSize: 9, lineHeight: '14px', padding: '0 3px', margin: 0 }}>
          执行中
        </Tag>
      ) : tool.status === 'error' ? (
        <Tooltip title={tool.outputPreview?.slice(0, 200)}>
          <Tag color="error" style={{ fontSize: 9, lineHeight: '14px', padding: '0 3px', margin: 0 }}>
            失败
          </Tag>
        </Tooltip>
      ) : (
        <Text type="secondary" style={{ fontSize: 10 }}>
          ✓
        </Text>
      )}
    </div>
  )
}

/** 单个子任务卡片 */
function TaskCard({ task }: { task: GoalTask }) {
  const isActive = task.status === 'in_progress'
  const hasTools = task.tools && task.tools.length > 0
  const runningTools = task.tools?.filter((t) => t.status === 'running') ?? []
  const doneTools = task.tools?.filter((t) => t.status === 'done') ?? []

  // 进行中或有工具调用的自动展开
  const defaultExpanded = isActive || hasTools
  const [expanded, setExpanded] = useState(defaultExpanded)

  return (
    <div style={getTaskCardStyle(task.status, isActive)}>
      {/* 任务头部 */}
      <div
        onClick={() => hasTools && setExpanded(!expanded)}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          padding: '8px 10px',
          cursor: hasTools ? 'pointer' : 'default',
          userSelect: 'none',
        }}
      >
        <TaskStatusIcon status={task.status} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <Text
              style={{
                fontSize: 13,
                fontWeight: isActive ? 600 : 400,
                color: task.status === 'done' ? '#52c41a' : task.status === 'failed' ? '#ff4d4f' : '#1a1a1a',
                textDecoration: task.status === 'done' ? 'line-through' : 'none',
              }}
            >
              {task.title}
            </Text>
            <StatusTag status={task.status} />
          </div>
          {task.dependencies && task.dependencies.length > 0 && (
            <Text type="secondary" style={{ fontSize: 10, display: 'block', marginTop: 1 }}>
              依赖: {task.dependencies.map((d) => `#${d}`).join(', ')}
            </Text>
          )}
        </div>

        {/* 工具计数 + 展开箭头 */}
        {hasTools && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 4, flexShrink: 0 }}>
            <ToolOutlined style={{ fontSize: 11, color: '#999' }} />
            <Text type="secondary" style={{ fontSize: 11 }}>
              {doneTools.length}/{task.tools!.length}
            </Text>
            <CaretRightOutlined
              style={{
                fontSize: 10,
                color: '#bbb',
                transform: expanded ? 'rotate(90deg)' : 'rotate(0deg)',
                transition: 'transform 0.2s',
              }}
            />
          </div>
        )}

        {/* 无工具时的耗时 */}
        {!hasTools && task.progress != null && task.progress > 0 && (
          <Text type="secondary" style={{ fontSize: 11 }}>
            {task.progress}%
          </Text>
        )}
      </div>

      {/* 工具调用列表（可折叠） */}
      {hasTools && expanded && (
        <div
          style={{
            padding: '0 10px 8px 33px',
            borderTop: '1px solid rgba(0,0,0,0.04)',
          }}
        >
          {task.tools!.map((tool, idx) => (
            <ToolRow key={`${tool.tool}-${idx}`} tool={tool} />
          ))}

          {/* 工具输出预览（已完成/失败的工具） */}
          {task.tools!.some((t) => (t.status === 'done' || t.status === 'error') && t.outputPreview) && (
            <div style={{ marginTop: 4 }}>
              {task.tools!
                .filter((t) => (t.status === 'done' || t.status === 'error') && t.outputPreview)
                .map((tool, idx) => (
                  <div
                    key={`output-${idx}`}
                    style={{
                      marginTop: 4,
                      padding: '4px 8px',
                      background: tool.status === 'error' ? '#fff2f0' : '#f6f8fa',
                      borderRadius: 4,
                      fontSize: 10,
                      maxHeight: 60,
                      overflow: 'hidden',
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-all',
                      color: tool.status === 'error' ? '#cf1322' : '#666',
                      fontFamily: 'monospace',
                    }}
                  >
                    {tool.outputPreview!.slice(0, 200)}{tool.outputPreview!.length > 200 ? '...' : ''}
                  </div>
                ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

/** 主组件 */
export function GoalTaskBoard({
  tasks,
  iterations = 0,
  maxIterations = 5,
  tokensUsed = 0,
  tokenBudget = 50000,
}: GoalTaskBoardProps) {
  const hasTasks = tasks && tasks.length > 0
  const completedCount = hasTasks ? tasks.filter((t) => t.status === 'done').length : 0
  const failedCount = hasTasks ? tasks.filter((t) => t.status === 'failed').length : 0
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
          <div style={{ display: 'flex', gap: 8 }}>
            <Text type="secondary" style={{ fontSize: 11 }}>
              ✅ {completedCount}/{tasks.length}
            </Text>
            {failedCount > 0 && (
              <Text style={{ fontSize: 11, color: '#ff4d4f' }}>
                ❌ {failedCount}
              </Text>
            )}
          </div>
        )}
      </div>

      {/* 空状态 */}
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
          status={progressPercent === 100 ? 'success' : failedCount > 0 ? 'exception' : 'active'}
          showInfo={false}
          style={{ marginBottom: 10 }}
        />
      )}

      {/* 子任务列表 */}
      {hasTasks && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {tasks.map((task) => (
            <TaskCard key={task.id} task={task} />
          ))}
        </div>
      )}

      {/* 底部统计 */}
      {hasTasks && (
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            marginTop: 10,
            paddingTop: 8,
            borderTop: '1px solid #f0f0f0',
          }}
        >
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
