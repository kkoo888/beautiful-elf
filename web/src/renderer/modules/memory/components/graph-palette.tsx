/** 节点 Palette — 左侧实体类型面板，拖拽添加实体节点 */

import { useCallback } from 'react'
import { Typography, Divider } from 'antd'
import { DragOutlined } from '@ant-design/icons'
import { useGraphStore } from './graph-store'
import type { Node } from 'reactflow'

const { Text } = Typography

const ENTITY_TEMPLATES = [
  { type: 'person',  label: '人物',   icon: '👤', color: '#E6F4FF', border: '#91CAFF' },
  { type: 'tech',    label: '技术',   icon: '🛠', color: '#E6FFFB', border: '#87E8DE' },
  { type: 'project', label: '项目',   icon: '📁', color: '#F9F0FF', border: '#D3ADF7' },
  { type: 'tool',    label: '工具',   icon: '🔧', color: '#F6FFED', border: '#B7EB8F' },
  { type: 'concept', label: '概念',   icon: '💡', color: '#FFF7E6', border: '#FFD591' },
  { type: 'org',     label: '组织',   icon: '🏢', color: '#F0F5FF', border: '#ADC6FF' },
]

export function NodePalette() {
  const { paletteOpen, nodes, setNodes, pushSnapshot } = useGraphStore()

  const handleAddNode = useCallback((template: typeof ENTITY_TEMPLATES[0]) => {
    pushSnapshot()
    const existing = nodes.filter(n => n.data?.entityType === template.type)
    const maxY = existing.reduce((max, n) => Math.max(max, n.position.y), 0)
    const newNode: Node = {
      id: `entity-new-${Date.now()}`,
      type: 'entity',
      position: { x: 100, y: maxY + 180 },
      data: { name: `新${template.label}`, entityType: template.type, description: '', mentionCount: 0, entityId: 0 },
    }
    setNodes([...nodes, newNode])
  }, [nodes, setNodes, pushSnapshot])

  const handleDragStart = useCallback((e: React.DragEvent, template: typeof ENTITY_TEMPLATES[0]) => {
    e.dataTransfer.setData('application/memory-node-type', template.type)
    e.dataTransfer.effectAllowed = 'move'
  }, [])

  if (!paletteOpen) return null

  return (
    <div style={{
      position: 'absolute', left: 8, top: 48, zIndex: 10,
      width: 160, background: 'rgba(255,255,255,0.92)',
      borderRadius: 6, border: '1px solid #f0f0f0',
      boxShadow: '0 1px 6px rgba(0,0,0,0.06)',
      padding: '10px 0',
    }}>
      <div style={{ padding: '0 12px 8px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Text strong style={{ fontSize: 13 }}>添加实体</Text>
        <DragOutlined style={{ fontSize: 11, color: '#bfbfbf' }} />
      </div>
      <Divider style={{ margin: '0 0 8px' }} />
      {ENTITY_TEMPLATES.map(template => (
        <div
          key={template.type}
          onClick={() => handleAddNode(template)}
          draggable
          onDragStart={(e) => handleDragStart(e, template)}
          style={{
            display: 'flex', alignItems: 'center', gap: 8,
            padding: '7px 12px', cursor: 'pointer',
            transition: 'background 0.15s',
          }}
          onMouseEnter={e => (e.currentTarget.style.background = '#f5f5f5')}
          onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
        >
          <div style={{
            width: 26, height: 26, borderRadius: 6,
            background: template.color, border: `1px solid ${template.border}`,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 14,
          }}>
            {template.icon}
          </div>
          <span style={{ fontSize: 13, fontWeight: 500 }}>{template.label}</span>
        </div>
      ))}
    </div>
  )
}
