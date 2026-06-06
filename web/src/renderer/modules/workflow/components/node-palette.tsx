/** 节点工具栏 - 拖拽添加节点到画布 */

import { Typography } from 'antd'
import type { DagNodeType } from '../types/workflow'

const { Text } = Typography

interface PaletteItem {
  type: DagNodeType
  label: string
  icon: string
  color: string
}

const PALETTE_ITEMS: PaletteItem[] = [
  { type: 'start', label: '开始', icon: '▶', color: '#52c41a' },
  { type: 'end', label: '结束', icon: '⏹', color: '#ff4d4f' },
  { type: 'task', label: '任务', icon: '📋', color: '#1677ff' },
  { type: 'condition', label: '条件', icon: '🔀', color: '#fa8c16' },
  { type: 'parallel', label: '并行', icon: '⚡', color: '#722ed1' },
]

function onDragStart(event: React.DragEvent, type: DagNodeType, label: string) {
  event.dataTransfer.setData('application/reactflow-type', type)
  event.dataTransfer.setData('application/reactflow-label', label)
  event.dataTransfer.effectAllowed = 'move'
}

export function NodePalette() {
  return (
    <div style={{ padding: '12px 0' }}>
      <Text
        type="secondary"
        style={{ fontSize: 12, padding: '0 16px', display: 'block', marginBottom: 8 }}
      >
        拖拽节点到画布
      </Text>
      {PALETTE_ITEMS.map((item) => (
        <div
          key={item.type}
          draggable
          onDragStart={(e) => onDragStart(e, item.type, item.label)}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            padding: '10px 16px',
            cursor: 'grab',
            borderRadius: 8,
            margin: '0 8px 6px',
            transition: 'background 0.15s',
            border: '1px solid var(--ant-color-border-secondary)',
            background: 'var(--ant-color-bg-container)',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = 'var(--ant-color-bg-text-hover)'
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = 'var(--ant-color-bg-container)'
          }}
        >
          <span style={{ fontSize: 18 }}>{item.icon}</span>
          <span style={{ fontSize: 13, fontWeight: 500 }}>{item.label}</span>
          <span
            style={{
              marginLeft: 'auto',
              width: 8,
              height: 8,
              borderRadius: '50%',
              background: item.color,
              flexShrink: 0,
            }}
          />
        </div>
      ))}
    </div>
  )
}
