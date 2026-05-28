/** 条件节点（菱形） */

import { memo } from 'react'
import { Handle, Position } from 'reactflow'
import type { NodeProps } from 'reactflow'
import { NODE_STATUS_STYLES } from './status-colors'

interface ConditionNodeData {
  label: string
  status: string
  [key: string]: unknown
}

function ConditionNodeComponent({ data }: NodeProps<ConditionNodeData>) {
  const statusStyle = NODE_STATUS_STYLES[data.status] ?? NODE_STATUS_STYLES.idle

  return (
    <div style={{ position: 'relative', width: 100, height: 100 }}>
      <Handle type="target" position={Position.Top} style={{ width: 8, height: 8, background: statusStyle.border }} />
      <div
        style={{
          width: 100,
          height: 100,
          transform: 'rotate(45deg)',
          borderRadius: 8,
          background: statusStyle.bg,
          border: `2px solid ${statusStyle.border}`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <span
          style={{
            transform: 'rotate(-45deg)',
            color: statusStyle.text,
            fontSize: 12,
            fontWeight: 600,
            textAlign: 'center',
            lineHeight: 1.2,
            maxWidth: 70,
            wordBreak: 'break-all',
          }}
        >
          {data.label}
        </span>
      </div>
      <Handle type="source" position={Position.Bottom} style={{ width: 8, height: 8, background: statusStyle.border }} />
      <Handle
        type="source"
        position={Position.Right}
        id="right"
        style={{ width: 8, height: 8, background: statusStyle.border }}
      />
    </div>
  )
}

export const ConditionNode = memo(ConditionNodeComponent)
