/** 节点右键菜单 — 借鉴 Dify ContextMenuContent 模式 */

import { useEffect, useRef } from 'react'
import { useGraphStore } from './graph-store'
import {
  EditOutlined,
  DeleteOutlined,
  DisconnectOutlined,
  EyeOutlined,
} from '@ant-design/icons'

interface MenuItem {
  key: string
  label: string
  icon: React.ReactNode
  danger?: boolean
  onClick: () => void
}

export function NodeContextMenu() {
  const { contextMenu, closeContextMenu } = useGraphStore()
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as HTMLElement)) {
        closeContextMenu()
      }
    }
    if (contextMenu) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [contextMenu, closeContextMenu])

  if (!contextMenu) return null

  const items: MenuItem[] = [
    {
      key: 'view',
      label: '查看详情',
      icon: <EyeOutlined />,
      onClick: () => {
        useGraphStore.getState().selectNode(contextMenu.nodeId)
        closeContextMenu()
      },
    },
    {
      key: 'edit',
      label: '编辑',
      icon: <EditOutlined />,
      onClick: () => {
        useGraphStore.getState().selectNode(contextMenu.nodeId)
        closeContextMenu()
      },
    },
    {
      key: 'disconnect',
      label: '断开所有连线',
      icon: <DisconnectOutlined />,
      onClick: () => {
        const { edges, setEdges, pushSnapshot } = useGraphStore.getState()
        pushSnapshot()
        setEdges(edges.filter(e => e.source !== contextMenu.nodeId && e.target !== contextMenu.nodeId))
        closeContextMenu()
      },
    },
    {
      key: 'delete',
      label: '删除节点',
      icon: <DeleteOutlined />,
      danger: true,
      onClick: () => {
        const { nodes, edges, setNodes, setEdges, pushSnapshot } = useGraphStore.getState()
        pushSnapshot()
        setNodes(nodes.filter(n => n.id !== contextMenu.nodeId))
        setEdges(edges.filter(e => e.source !== contextMenu.nodeId && e.target !== contextMenu.nodeId))
        closeContextMenu()
      },
    },
  ]

  return (
    <div
      ref={ref}
      style={{
        position: 'fixed',
        left: contextMenu.x,
        top: contextMenu.y,
        zIndex: 1000,
        background: '#fafafa',
        borderRadius: 6,
        boxShadow: '0 4px 12px rgba(0,0,0,0.08)',
        border: '1px solid #f0f0f0',
        padding: '4px 0',
        minWidth: 160,
      }}
    >
      {items.map(item => (
        <div
          key={item.key}
          onClick={item.onClick}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            padding: '8px 12px',
            cursor: 'pointer',
            fontSize: 13,
            color: item.danger ? '#ff4d4f' : '#262626',
            transition: 'background 0.15s',
          }}
          onMouseEnter={e => (e.currentTarget.style.background = '#f5f5f5')}
          onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
        >
          {item.icon}
          {item.label}
        </div>
      ))}
    </div>
  )
}

export function EdgeContextMenu() {
  const { edgeContextMenu, closeEdgeContextMenu } = useGraphStore()
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as HTMLElement)) {
        closeEdgeContextMenu()
      }
    }
    if (edgeContextMenu) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [edgeContextMenu, closeEdgeContextMenu])

  if (!edgeContextMenu) return null

  return (
    <div
      ref={ref}
      style={{
        position: 'fixed',
        left: edgeContextMenu.x,
        top: edgeContextMenu.y,
        zIndex: 1000,
        background: '#fafafa',
        borderRadius: 6,
        boxShadow: '0 4px 12px rgba(0,0,0,0.08)',
        border: '1px solid #f0f0f0',
        padding: '4px 0',
        minWidth: 140,
      }}
    >
      <div
        onClick={() => {
          const { edges, setEdges, pushSnapshot } = useGraphStore.getState()
          pushSnapshot()
          setEdges(edges.filter(e => e.id !== edgeContextMenu.edgeId))
          closeEdgeContextMenu()
        }}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          padding: '8px 12px',
          cursor: 'pointer',
          fontSize: 13,
          color: '#ff4d4f',
        }}
        onMouseEnter={e => (e.currentTarget.style.background = '#f5f5f5')}
        onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
      >
        <DeleteOutlined />
        删除连线
      </div>
    </div>
  )
}
