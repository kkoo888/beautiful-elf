import { Typography, Tag, Spin } from 'antd'
import {
  FileOutlined,
  SearchOutlined,
  CodeOutlined,
  ReadOutlined,
  ToolOutlined,
  RobotOutlined,
} from '@ant-design/icons'

const { Text } = Typography

interface ExecutionStatusProps {
  isExecuting: boolean
  currentStep?: string
  currentTool?: string
  currentFile?: string
  currentAction?: string
}

export function ExecutionStatus({
  isExecuting,
  currentStep,
  currentTool,
  currentFile,
  currentAction,
}: ExecutionStatusProps) {
  if (!isExecuting) return null

  const getStepIcon = (step?: string) => {
    if (!step) return <RobotOutlined />
    if (step.includes('search') || step.includes('web')) return <SearchOutlined />
    if (step.includes('file') || step.includes('read') || step.includes('write')) return <FileOutlined />
    if (step.includes('code') || step.includes('exec')) return <CodeOutlined />
    if (step.includes('memory') || step.includes('context')) return <ReadOutlined />
    return <ToolOutlined />
  }

  const getStepLabel = (step?: string) => {
    if (!step) return '执行中'
    const labels: Record<string, string> = {
      llm: '生成回答',
      model_select: '选择模型',
      intent: '意图识别',
      context: '检索上下文',
      memory_save: '保存记忆',
      goal_subtasks: '规划子任务',
      goal_task_start: '开始子任务',
      goal_task_done: '完成子任务',
      goal_replan: '重规划',
      eval: '质量评估',
    }
    return labels[step] || step
  }

  return (
    <div style={{
      padding: '8px 16px',
      background: '#e6f4ff',
      borderBottom: '1px solid #91caff',
      animation: 'slideDown 0.2s ease-out'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <Spin size="small" />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            {getStepIcon(currentStep)}
            <Text style={{ fontSize: 13, fontWeight: 500, color: '#1677ff', margin: 0 }}>
              {getStepLabel(currentStep)}
            </Text>
          </div>
          {(currentTool || currentFile || currentAction) && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 4, flexWrap: 'wrap' }}>
              {currentTool && (
                <Tag color="blue" style={{ fontSize: 11, lineHeight: '18px', padding: '0 6px', margin: 0 }}>
                  🔧 {currentTool}
                </Tag>
              )}
              {currentFile && (
                <Tag color="green" style={{ fontSize: 11, lineHeight: '18px', padding: '0 6px', margin: 0 }}>
                  📄 {currentFile}
                </Tag>
              )}
              {currentAction && (
                <Text style={{ fontSize: 12, margin: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} type="secondary">
                  {currentAction}
                </Text>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
