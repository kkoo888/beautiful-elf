/** 节点 Palette — 左侧节点面板，对标 Dify Block Selector

功能：
  - 展示可用节点类型
  - 点击快速添加到画布
  - 分类筛选
*/

import { useCallback } from 'react'
import { Typography, Divider } from 'antd'
import {
  FileTextOutlined,
  BulbOutlined,
} from '@ant-design/icons'
import { useGraphStore } from './graph-store'
import type { Node } from 'reactflow'

const { Text } = Typography

const NODE_TEMPLATES = [
  {
    type: 'observation',
    label: '提炼记忆',
    icon: <BulbOutlined style={{ color: '#E8913A', fontSize: 16 }} />,
    description: '从日志中提炼的知识',
    color: '#FFF7ED',
    borderColor: '#FDBA74',
    createData: () => ({
      content: '新提炼记忆（点击编辑）',
      category: 'decisions',
      freshness: 'new',
      obsId: 0,
      sources: [],
    }),
  },
  {
    type: 'dailyLog',
    label: '日志节点',
    icon: <FileTextOutlined style={{ color: '#3BA0E8', fontSize: 16 }} />,
    description: '标记一条日志',
    color: '#E6F4FF',
    borderColor: '#91CAFF',
    createData: () => ({
      title: `日志 ${new Date().toLocaleDateString('zh-CN')}`,
      wordCount: 0,
      memoryId: '',
    }),
  },
]

export function NodePalette() {
  const { paletteOpen, nodes, setNodes, pushSnapshot } = useGraphStore()

  const handleAddNode = useCallback((template: typeof NODE_TEMPLATES[0]) => {
    pushSnapshot()

    // 找到合适的放置位置
    const existingObs = nodes.filter(n => n.type === 'observation')
    const maxY = existingObs.reduce((max, n) => Math.max(max, n.position.y), 0)

    const newNode: Node = {
      id: `obs-new-${Date.now()}`,
      type: template.type,
      position: { x: 450, y: maxY + 120 },
      data: template.createData(),
    }

    setNodes([...nodes, newNode])
  }, [nodes, setNodes, pushSnapshot])

  if (!paletteOpen) return null

  return (
    <div style={{
      position: 'absolute', left: 8, top: 48, zIndex: 10,
      width: 170, background: 'rgba(255,255,255,0.92)',
      borderRadius: 6, border: '1px solid #f0f0f0',
      boxShadow: '0 1px 6px rgba(0,0,0,0.06)',
      padding: '10px 0',
    }}>
      <div style={{ padding: '0 12px 8px' }}>
        <Text strong style={{ fontSize: 13 }}>添加节点</Text>
      </div>
      <Divider style={{ margin: '0 0 8px' }} />
      {NODE_TEMPLATES.map(template => (
        <div
          key={template.type}
          onClick={() => handleAddNode(template)}
          style={{
            display: 'flex', alignItems: 'center', gap: 8,
            padding: '8px 12px', cursor: 'pointer',
            transition: 'background 0.15s',
          }}
          onMouseEnter={e => (e.currentTarget.style.background = '#f5f5f5')}
          onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
        >
          <div style={{
            width: 28, height: 28, borderRadius: 6,
            background: template.color, border: `1px solid ${template.borderColor}`,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            {template.icon}
          </div>
          <div>
            <div style={{ fontSize: 13, fontWeight: 500 }}>{template.label}</div>
            <div style={{ fontSize: 11, color: '#8c8c8c' }}>{template.description}</div>
          </div>
        </div>
      ))}
    </div>
  )
}
