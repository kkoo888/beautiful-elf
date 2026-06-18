/** 记忆关系图 — 基于 Dify 模式重构

借鉴 Dify 核心设计：
  - Zustand store 统一状态管理（graph-store.ts）
  - 点击节点 → 右侧 Drawer 属性面板（graph-detail-drawer.tsx）
  - 右键菜单 → 编辑/删除/断开连线（graph-context-menu.tsx）
  - 顶部搜索 + 分类筛选（graph-toolbar.tsx）
  - 节点选中高亮 + 连线样式增强
*/

import { useState, useEffect, useCallback, useMemo } from 'react'
import ReactFlow, {
  Controls,
  Background,
  MiniMap,
  addEdge,
  useNodesState,
  useEdgesState,
  BackgroundVariant,
  MarkerType,
  type Connection,
  type Edge,
  type Node,
  type OnConnect,
  type OnNodeContextMenu,
  type OnEdgeContextMenu,
} from 'reactflow'
import 'reactflow/dist/style.css'
import { Spin, Empty, App } from 'antd'
import { FileTextOutlined, BulbOutlined } from '@ant-design/icons'
import {
  listObservations,
  fetchDailyLogs,
  createObservationSource,
  deleteObservationSource,
} from '../services/memory-api'
import type { Observation, MarkdownMemoryEntry } from '../services/memory-api'
import { useGraphStore } from './graph-store'
import { NodeContextMenu, EdgeContextMenu } from './graph-context-menu'
import { NodeDetailDrawer } from './graph-detail-drawer'
import { GraphToolbar } from './graph-toolbar'

// ── 样式常量 ──────────────────────────────────────────────

const COLORS = {
  primary: '#E8913A',
  info: '#3BA0E8',
  dailyBg: '#E6F4FF',
  dailyBorder: '#91CAFF',
  dailySelected: '#1890ff',
  obsBg: '#FFF7ED',
  obsBorder: '#FDBA74',
  obsSelected: '#E8913A',
  edge: '#BFBFBF',
  edgeActive: '#E8913A',
  dimmed: '#d9d9d9',
}

const CATEGORY_ICONS: Record<string, string> = {
  decisions: '🔑',
  pitfalls: '🐛',
  preferences: '👤',
  status: '📦',
}

// ── 自定义节点组件（增强版：支持选中高亮 + 搜索半透明）──

function DailyLogNode({ data, selected }: { data: any; selected?: boolean }) {
  const searchKeyword = useGraphStore(s => s.searchKeyword)
  const dimmed = searchKeyword && !(data.title || '').toLowerCase().includes(searchKeyword.toLowerCase())

  return (
    <div style={{
      padding: '10px 14px',
      background: selected ? '#e6f7ff' : COLORS.dailyBg,
      border: `2px solid ${selected ? COLORS.dailySelected : COLORS.dailyBorder}`,
      borderRadius: 8,
      fontSize: 12,
      minWidth: 120,
      cursor: 'grab',
      opacity: dimmed ? 0.3 : 1,
      transition: 'all 0.2s',
      boxShadow: selected ? '0 0 0 2px rgba(24,144,255,0.2)' : 'none',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
        <FileTextOutlined style={{ color: COLORS.info, fontSize: 14 }} />
        <strong style={{ fontSize: 13 }}>{data.title}</strong>
      </div>
      <span style={{ color: '#8c8c8c', fontSize: 11 }}>{data.wordCount} 字</span>
    </div>
  )
}

function ObservationNode({ data, selected }: { data: any; selected?: boolean }) {
  const searchKeyword = useGraphStore(s => s.searchKeyword)
  const categoryFilter = useGraphStore(s => s.categoryFilter)
  const dimmedBySearch = searchKeyword && !(data.content || '').toLowerCase().includes(searchKeyword.toLowerCase())
  const dimmedByCategory = categoryFilter !== 'all' && data.category !== categoryFilter
  const dimmed = dimmedBySearch || dimmedByCategory

  const icon = CATEGORY_ICONS[data.category] || '📌'
  const preview = data.content?.length > 50 ? data.content.slice(0, 50) + '...' : (data.content || '')

  return (
    <div style={{
      padding: '10px 14px',
      background: selected ? '#fff7e6' : COLORS.obsBg,
      border: `2px solid ${selected ? COLORS.obsSelected : COLORS.obsBorder}`,
      borderRadius: 8,
      fontSize: 12,
      minWidth: 140,
      maxWidth: 200,
      cursor: 'grab',
      opacity: dimmed ? 0.3 : 1,
      transition: 'all 0.2s',
      boxShadow: selected ? '0 0 0 2px rgba(232,145,58,0.2)' : 'none',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 4 }}>
        <span>{icon}</span>
        <strong style={{ fontSize: 12 }}>{preview.split('\n')[0]}</strong>
      </div>
      <span style={{ color: '#8c8c8c', fontSize: 11 }}>{data.freshness}</span>
    </div>
  )
}

const nodeTypes = {
  dailyLog: DailyLogNode,
  observation: ObservationNode,
}

// ── 主组件 ──────────────────────────────────────────────────

export function MemoryGraphTab() {
  const { message: msg } = App.useApp()
  const {
    loading, setLoading,
    observations, setObservations,
    dailyLogs, setDailyLogs,
    nodes: storeNodes, edges: storeEdges,
    setNodes: setStoreNodes, setEdges: setStoreEdges,
    selectNode, openContextMenu, openEdgeContextMenu,
  } = useGraphStore()

  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])

  // ── 同步 React Flow 状态到 Store ──
  useEffect(() => { setStoreNodes(nodes) }, [nodes])
  useEffect(() => { setStoreEdges(edges) }, [edges])

  // ── 加载数据 ──
  useEffect(() => { loadData() }, [])

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const [obsResult, logsResult] = await Promise.all([
        listObservations({ pageSize: 100 }),
        fetchDailyLogs(30),
      ])
      setObservations(obsResult.items)
      setDailyLogs(logsResult)
      buildGraph(obsResult.items, logsResult)
    } catch {} finally {
      setLoading(false)
    }
  }, [])

  // ── 构建图 ──
  const buildGraph = useCallback((obs: Observation[], logs: MarkdownMemoryEntry[]) => {
    const newNodes: Node[] = []
    const newEdges: Edge[] = []

    logs.forEach((log, i) => {
      newNodes.push({
        id: `log-${log.id}`,
        type: 'dailyLog',
        position: { x: 50, y: i * 100 + 50 },
        data: { title: log.title, wordCount: log.wordCount, memoryId: log.id },
      })
    })

    obs.forEach((ob, i) => {
      newNodes.push({
        id: `obs-${ob.id}`,
        type: 'observation',
        position: { x: 450, y: i * 120 + 50 },
        data: { content: ob.content, category: ob.category, freshness: ob.freshness, obsId: ob.id, sources: ob.sources },
      })

      if (ob.sources) {
        ob.sources.forEach(src => {
          if (logs.some(l => l.id === String(src.logId))) {
            newEdges.push({
              id: `edge-${src.sourceId}`,
              source: `log-${src.logId}`,
              target: `obs-${ob.id}`,
              animated: false,
              style: { stroke: COLORS.edge, strokeWidth: 2 },
              markerEnd: { type: MarkerType.ArrowClosed, color: COLORS.edge },
              data: { sourceId: src.sourceId },
            })
          }
        })
      }
    })

    setNodes(newNodes)
    setEdges(newEdges)
  }, [])

  // ── 连线回调 ──
  const onConnect: OnConnect = useCallback(async (connection: Connection) => {
    if (!connection.source || !connection.target) return
    if (!connection.source.startsWith('log-') || !connection.target.startsWith('obs-')) {
      msg.warning('只能从日志拖拽到提炼记忆')
      return
    }

    const logId = parseInt(connection.source.replace('log-', ''))
    const obsId = parseInt(connection.target.replace('obs-', ''))

    const tempEdgeId = `edge-temp-${Date.now()}`
    setEdges(eds => addEdge({
      ...connection,
      id: tempEdgeId,
      animated: true,
      style: { stroke: COLORS.edgeActive, strokeWidth: 2 },
      markerEnd: { type: MarkerType.ArrowClosed, color: COLORS.edgeActive },
    }, eds))

    try {
      const result = await createObservationSource(obsId, logId)
      setEdges(eds => eds.map(e =>
        e.id === tempEdgeId
          ? { ...e, id: `edge-${result.id}`, animated: false, style: { stroke: COLORS.edge, strokeWidth: 2 }, markerEnd: { type: MarkerType.ArrowClosed, color: COLORS.edge } }
          : e
      ))
      msg.success('关联创建成功')
    } catch {
      setEdges(eds => eds.filter(e => e.id !== tempEdgeId))
      msg.error('关联创建失败')
    }
  }, [])

  // ── 节点点击 → 选中 + 打开详情 ──
  const handleNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    selectNode(node.id)
  }, [selectNode])

  // ── 节点右键 → 上下文菜单 ──
  const handleNodeContextMenu: OnNodeContextMenu = useCallback((event, node) => {
    event.preventDefault()
    openContextMenu(node.id, event.clientX, event.clientY)
  }, [openContextMenu])

  // ── 边右键 → 上下文菜单 ──
  const handleEdgeContextMenu: OnEdgeContextMenu = useCallback((event, edge) => {
    event.preventDefault()
    openEdgeContextMenu(edge.id, event.clientX, event.clientY)
  }, [openEdgeContextMenu])

  // ── 边点击 → 删除关联（保留原逻辑）──
  const onEdgeClick = useCallback(async (_: React.MouseEvent, edge: Edge) => {
    const sourceId = edge.data?.sourceId
    if (!sourceId) return
    setEdges(eds => eds.filter(e => e.id !== edge.id))
    try {
      await deleteObservationSource(sourceId)
      msg.success('关联已删除')
    } catch {
      setEdges(eds => [...eds, edge])
      msg.error('删除失败')
    }
  }, [])

  // ── Loading ──
  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
        <Spin />
      </div>
    )
  }

  if (observations.length === 0 && dailyLogs.length === 0) {
    return <Empty description="暂无数据，请先提炼记忆" image={Empty.PRESENTED_IMAGE_SIMPLE} />
  }

  return (
    <div style={{ height: '100%', width: '100%', borderRadius: 8, overflow: 'hidden', border: '1px solid #f0f0f0', position: 'relative' }}>
      {/* 搜索 + 筛选 */}
      <GraphToolbar />

      {/* 右键菜单 */}
      <NodeContextMenu />
      <EdgeContextMenu />

      {/* 详情抽屉 */}
      <NodeDetailDrawer />

      {/* 画布 */}
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodeClick={handleNodeClick}
        onNodeContextMenu={handleNodeContextMenu}
        onEdgeContextMenu={handleEdgeContextMenu}
        onEdgeClick={onEdgeClick}
        nodeTypes={nodeTypes}
        fitView
        deleteKeyCode={null}
        attributionPosition="bottom-left"
        style={{ background: '#fafafa' }}
      >
        <Controls />
        <MiniMap
          nodeColor={node => node.type === 'dailyLog' ? COLORS.dailyBg : COLORS.obsBg}
          maskColor="rgba(0,0,0,0.08)"
          style={{ border: '1px solid #f0f0f0', borderRadius: 4 }}
        />
        <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="#e8e8e8" />
      </ReactFlow>

      {/* 图例 */}
      <div style={{
        position: 'absolute', bottom: 12, left: 12,
        display: 'flex', gap: 16, padding: '6px 12px',
        background: 'rgba(255,255,255,0.9)', borderRadius: 6,
        border: '1px solid #f0f0f0', fontSize: 12,
      }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <span style={{ width: 12, height: 12, background: COLORS.dailyBg, border: `1px solid ${COLORS.dailyBorder}`, borderRadius: 3, display: 'inline-block' }} />
          Daily Log
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <span style={{ width: 12, height: 12, background: COLORS.obsBg, border: `1px solid ${COLORS.obsBorder}`, borderRadius: 3, display: 'inline-block' }} />
          提炼记忆
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <span style={{ width: 20, height: 2, background: COLORS.edge, display: 'inline-block' }} />
          点击节点查看详情 · 右键操作 · 拖拽连线
        </span>
      </div>
    </div>
  )
}
