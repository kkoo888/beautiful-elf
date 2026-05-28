/** 开始节点 */

import { memo } from 'react'
import { Handle, Position } from 'reactflow'
import type { NodeProps } from 'reactflow'
import type { WorkflowNode } from '../../types/workflow'
import { NODE_STATUS_STYLES } from './status-colors'

function StartNodeComponent({
  data,
}: NodeProps<WorkflowNode['config'] & { label: string; status: string }>) {
  const statusStyle =
    NODE_STATUS_STYLES[data.status as keyof typeof NODE_STATUS_STYLES] ?? NODE_STATUS_STYLES.idle

  return (
    <div
      style={{
        padding: '8px 24px',
        borderRadius: 24,
        background: statusStyle.bg,
        border: `2px solid ${statusStyle.border}`,
        color: statusStyle.text,
        fontSize: 13,
        fontWeight: 600,
        minWidth: 80,
        textAlign: 'center',
        boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
      }}
    >
      {data.label}
      <Handle
        type="source"
        position={Position.Bottom}
        style={{ width: 8, height: 8, background: statusStyle.border }}
      />
    </div>
  )
}

export const StartNode = memo(StartNodeComponent)
