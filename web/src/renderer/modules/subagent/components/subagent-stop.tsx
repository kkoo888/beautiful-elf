/** 终止按钮组件（Popconfirm 确认） */

import { Button, Popconfirm } from 'antd'
import { StopOutlined } from '@ant-design/icons'
import type { SubagentStatus } from '../types/subagent'

interface SubagentStopProps {
  runId: string
  status: SubagentStatus
  onStop: (id: string) => void
}

export function SubagentStop({ runId, status, onStop }: SubagentStopProps) {
  if (status !== 'running') return null

  return (
    <Popconfirm
      title="确定终止此子代理？"
      description="终止后无法恢复运行状态"
      onConfirm={() => onStop(runId)}
      okText="终止"
      cancelText="取消"
      okButtonProps={{ danger: true }}
    >
      <Button type="text" size="small" danger icon={<StopOutlined />} />
    </Popconfirm>
  )
}
