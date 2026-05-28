/** 并行节点 */

import { memo } from 'react'
import { Handle, Position } from 'reactflow'
import type { NodeProps } from 'reactflow'
import { NODE_STATUS_STYLES } from './status-colors'

interface ParallelNodeData {
  label: string
  status: string
  [key: string]: unknown
}

function ParallelNodeComponent({ data }: NodeProps<ParallelNodeData>) {
  const statusStyle = NODE_STATUS_STYLES[data.status] ?? NODE_STATUS_STYLES.idle

  return (
    <div
      style={{
        padding: '10px 20px',
        borderRadius: 8,
        background: statusStyle.bg,
        border: `2px dashed ${statusStyle.border}`,
        color: statusStyle.text,
        fontSize: 13,
        fontWeight: 500,
        minWidth: 120,
        textAlign: 'center',
        boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
      }}
    >
      <Handle
        type="target"
        position={Position.Top}
        style={{ width: 8, height: 8, background: statusStyle.border }}
      />
      ⚡ {data.label}
      <Handle
        type="source"
        position={Position.Bottom}
        id="bottom-left"
        style={{ left: '30%', width: 8, height: 8, background: statusStyle.border }}
      />
      <Handle
        type="source"
        position={Position.Bottom}
        id="bottom-right"
        style={{ left: '70%', width: 8, height: 8, background: statusStyle.border }}
      />
    </div>
  )
}

export const ParallelNode = memo(ParallelNodeComponent)
