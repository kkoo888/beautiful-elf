/** 结束节点 */

import { memo } from 'react'
import { Handle, Position } from 'reactflow'
import type { NodeProps } from 'reactflow'
import { NODE_STATUS_STYLES } from './status-colors'

interface EndNodeData {
  label: string
  status: string
  [key: string]: unknown
}

function EndNodeComponent({ data }: NodeProps<EndNodeData>) {
  const statusStyle = NODE_STATUS_STYLES[data.status] ?? NODE_STATUS_STYLES.idle

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
      <Handle
        type="target"
        position={Position.Top}
        style={{ width: 8, height: 8, background: statusStyle.border }}
      />
      {data.label}
    </div>
  )
}

export const EndNode = memo(EndNodeComponent)
