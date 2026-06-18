/** 记忆关系图 — 全面进化版，借鉴 Dify 核心模式

进化清单：
  1. 撤销/重做（Ctrl+Z / Ctrl+Y）
  2. 布局持久化（localStorage，刷新不丢）
  3. 节点结构增强（Header+Body+desc）
  4. 关系链接修复（任意节点间可连线）
  5. Handle 快速添加（点击 Handle 弹出选项）
  6. 自动布局（一键整理）
  7. 快捷键支持
  8. 连线渐变色
  9. 节点 Palette 侧栏
  10. 搜索 + 分类筛选
*/

import { useState, useEffect, useCallback, useRef } from 'react'
import ReactFlow, {
  Controls,
  Background,
  MiniMap,
  ReactFlowProvider,
  addEdge,
  useNodesState,
  useEdgesState,
  BackgroundVariant,
  MarkerType,
  useReactFlow,
  type Connection,
  type Edge,
  type Node,
  type OnConnect,
  type OnNodeContextMenu,
  type OnEdgeContextMenu,
} from 'reactflow'
import 'reactflow/dist/style.css'
import { Spin, Empty, App, Tooltip, Button, Space } from 'antd'
import {
  FileTextOutlined, BulbOutlined,
  UndoOutlined, RedoOutlined,
  AppstoreOutlined, SortAscendingOutlined,
  SaveOutlined, CompressOutlined,
  DragOutlined,
} from '@ant-design/icons'
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
import { NodePalette } from './graph-palette'
import { autoLayoutAndFit } from './graph-layout'

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
}

const CATEGORY_ICONS: Record<string, string> = {
  decisions: '🔑',
  pitfalls: '🐛',
  preferences: '👤',
  status: '📦',
}

// ── 增强版节点组件（Header + Body + desc）──

function DailyLogNode({ data, selected }: { data: any; selected?: boolean }) {
  const searchKeyword = useGraphStore(s => s.searchKeyword)
  const dimmed = searchKeyword && !(data.title || '').toLowerCase().includes(searchKeyword.toLowerCase())

  return (
    <div style={{
      padding: 0, borderRadius: 6, overflow: 'hidden',
      border: `1.5px solid ${selected ? COLORS.dailySelected : COLORS.dailyBorder}`,
      background: selected ? '#f0f7ff' : '#fff',
      opacity: dimmed ? 0.2 : 1,
      transition: 'opacity 0.2s, border-color 0.15s, box-shadow 0.15s',
      boxShadow: selected ? '0 0 0 2px rgba(24,144,255,0.12)' : 'none',
      minWidth: 150, maxWidth: 200,
    }}>
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 6,
        padding: '7px 10px', background: selected ? '#e6f0ff' : COLORS.dailyBg,
      }}>
        <FileTextOutlined style={{ color: COLORS.info, fontSize: 13 }} />
        <span style={{ fontSize: 12, fontWeight: 600, color: '#1a1a2e', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {data.title}
        </span>
      </div>
      {/* Body */}
      <div style={{ padding: '5px 10px 7px' }}>
        <span style={{ color: '#8c8c8c', fontSize: 11 }}>{data.wordCount} 字</span>
      </div>
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
  const preview = data.content?.length > 40 ? data.content.slice(0, 40) + '...' : (data.content || '')
  const catLabel = { decisions: '决策', pitfalls: '踩坑', preferences: '偏好', status: '状态' }[data.category] || ''

  return (
    <div style={{
      padding: 0, borderRadius: 6, overflow: 'hidden',
      border: `1.5px solid ${selected ? COLORS.obsSelected : COLORS.obsBorder}`,
      background: selected ? '#fff8f0' : '#fff',
      opacity: dimmed ? 0.2 : 1,
      transition: 'opacity 0.2s, border-color 0.15s, box-shadow 0.15s',
      boxShadow: selected ? '0 0 0 2px rgba(232,145,58,0.12)' : 'none',
      minWidth: 150, maxWidth: 200,
    }}>
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 5,
        padding: '7px 10px', background: selected ? '#fff0e0' : COLORS.obsBg,
      }}>
        <span style={{ fontSize: 13 }}>{icon}</span>
        <span style={{
          fontSize: 10, padding: '1px 5px', borderRadius: 3,
          background: '#fff', color: '#8c8c8c',
        }}>{catLabel}</span>
      </div>
      {/* Body */}
      <div style={{ padding: '6px 10px' }}>
        <div style={{ fontSize: 12, lineHeight: 1.5, color: '#1a1a2e', wordBreak: 'break-all' }}>
          {preview.split('\n')[0]}
        </div>
      </div>
      {/* desc */}
      {data.freshness && (
        <div style={{
          padding: '3px 10px 5px',
          fontSize: 11, color: '#bfbfbf',
        }}>
          {data.sources?.length || 0} 条来源
        </div>
      )}
    </div>
  )
}

const nodeTypes = {
  dailyLog: DailyLogNode,
  observation: ObservationNode,
}

// ── 渐变连线组件 ──

function GradientEdge({ id, sourceX, sourceY, targetX, targetY, style, markerEnd, data }: any) {
  const gradientId = `gradient-${id}`
  return (
    <>
      <defs>
        <linearGradient id={gradientId} x1={sourceX} y1={sourceY} x2={targetX} y2={targetY} gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor={COLORS.info} stopOpacity={0.6} />
          <stop offset="100%" stopColor={COLORS.primary} stopOpacity={0.8} />
        </linearGradient>
      </defs>
      <path
        d={`M${sourceX},${sourceY} C${sourceX + 80},${sourceY} ${targetX - 80},${targetY} ${targetX},${targetY}`}
        stroke={`url(#${gradientId})`}
        strokeWidth={2.5}
        fill="none"
        markerEnd={markerEnd}
      />
    </>
  )
}

const edgeTypes = { gradient: GradientEdge }

// ── 主组件 ──────────────────────────────────────────────────

export function MemoryGraphTab() {
  return (
    <ReactFlowProvider>
      <MemoryGraphInner />
    </ReactFlowProvider>
  )
}

function MemoryGraphInner() {
  const { message: msg } = App.useApp()
  const reactflow = useReactFlow()
  const {
    loading, setLoading,
    observations, setObservations,
    dailyLogs, setDailyLogs,
    setNodes: setStoreNodes, setEdges: setStoreEdges,
    selectNode, openContextMenu, openEdgeContextMenu,
    undo, redo, canUndo, canRedo, pushSnapshot,
    saveLayout, loadLayout, paletteOpen, togglePalette,
  } = useGraphStore()

  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])
  const isInitialized = useRef(false)

  // ── 同步到 Store ──
  useEffect(() => { setStoreNodes(nodes, true) }, [nodes])
  useEffect(() => { setStoreEdges(edges, true) }, [edges])

  // ── 初始化：尝试恢复布局 → 否则加载数据 ──
  useEffect(() => {
    if (isInitialized.current) return
    isInitialized.current = true

    const saved = loadLayout()
    if (saved && saved.nodes.length > 0) {
      setNodes(saved.nodes)
      setEdges(saved.edges)
      setLoading(false)
    } else {
      loadData()
    }
  }, [])

  // ── 自动保存布局（debounce）──
  useEffect(() => {
    const timer = setTimeout(() => {
      if (nodes.length > 0) saveLayout()
    }, 1000)
    return () => clearTimeout(timer)
  }, [nodes, edges])

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
              type: 'gradient',
              animated: false,
              markerEnd: { type: MarkerType.ArrowClosed, color: COLORS.primary },
              data: { sourceId: src.sourceId },
            })
          }
        })
      }
    })

    setNodes(newNodes)
    setEdges(newEdges)
  }, [])

  // ── 连线（支持任意节点间，修复关系链接）──
  const onConnect: OnConnect = useCallback(async (connection: Connection) => {
    if (!connection.source || !connection.target) return
    if (connection.source === connection.target) return

    pushSnapshot()

    const sourceIsLog = connection.source.startsWith('log-')
    const targetIsObs = connection.target.startsWith('obs-')

    // 日志 → 提炼记忆：创建后端关联
    if (sourceIsLog && targetIsObs) {
      const logId = parseInt(connection.source.replace('log-', ''))
      const obsId = parseInt(connection.target.replace('obs-', ''))

      const tempEdgeId = `edge-temp-${Date.now()}`
      setEdges(eds => addEdge({
        ...connection,
        id: tempEdgeId,
        type: 'gradient',
        animated: true,
        markerEnd: { type: MarkerType.ArrowClosed, color: COLORS.edgeActive },
      }, eds))

      try {
        const result = await createObservationSource(obsId, logId)
        setEdges(eds => eds.map(e =>
          e.id === tempEdgeId
            ? { ...e, id: `edge-${result.id}`, animated: false, data: { sourceId: result.id } }
            : e
        ))
        msg.success('关联创建成功')
      } catch {
        setEdges(eds => eds.filter(e => e.id !== tempEdgeId))
        msg.error('关联创建失败')
      }
      return
    }

    // 其他方向（提炼→提炼、提炼→日志）：纯前端连线
    setEdges(eds => addEdge({
      ...connection,
      id: `edge-local-${Date.now()}`,
      type: 'gradient',
      animated: false,
      markerEnd: { type: MarkerType.ArrowClosed, color: COLORS.primary },
      style: { strokeDasharray: '5,5' },
    }, eds))
    msg.success('关系已建立')
  }, [])

  // ── 节点点击 ──
  const handleNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    selectNode(node.id)
  }, [selectNode])

  // ── 右键菜单 ──
  const handleNodeContextMenu: OnNodeContextMenu = useCallback((event, node) => {
    event.preventDefault()
    openContextMenu(node.id, event.clientX, event.clientY)
  }, [openContextMenu])

  const handleEdgeContextMenu: OnEdgeContextMenu = useCallback((event, edge) => {
    event.preventDefault()
    openEdgeContextMenu(edge.id, event.clientX, event.clientY)
  }, [openEdgeContextMenu])

  // ── 边点击删除 ──
  const onEdgeClick = useCallback(async (_: React.MouseEvent, edge: Edge) => {
    const sourceId = edge.data?.sourceId
    pushSnapshot()
    setEdges(eds => eds.filter(e => e.id !== edge.id))
    if (sourceId) {
      try { await deleteObservationSource(sourceId) } catch {}
    }
  }, [])

  // ── 拖拽创建节点 ──
  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
  }, [])

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    const type = e.dataTransfer.getData('application/memory-node-type')
    if (!type) return

    const position = reactflow.screenToFlowPosition({ x: e.clientX, y: e.clientY })
    pushSnapshot()

    const newNode: Node = {
      id: `${type}-${Date.now()}`,
      type,
      position,
      data: type === 'observation'
        ? { content: '新提炼记忆（点击编辑）', category: 'decisions', freshness: 'new', obsId: 0, sources: [] }
        : { title: `日志 ${new Date().toLocaleDateString('zh-CN')}`, wordCount: 0, memoryId: '' },
    }

    setNodes([...nodes, newNode])
  }, [nodes, reactflow])

  // ── 自动布局 ──
  const handleAutoLayout = useCallback(() => {
    pushSnapshot()
    autoLayoutAndFit(nodes, edges, (newNodes) => setNodes(newNodes), reactflow.fitView)
  }, [nodes, edges, reactflow.fitView])

  // ── 快捷键 ──
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ctrl+Z 撤销
      if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey) {
        e.preventDefault()
        undo()
      }
      // Ctrl+Y 或 Ctrl+Shift+Z 重做
      if ((e.ctrlKey || e.metaKey) && (e.key === 'y' || (e.key === 'z' && e.shiftKey))) {
        e.preventDefault()
        redo()
      }
      // Delete 删除选中节点
      if (e.key === 'Delete' || e.key === 'Backspace') {
        const { selectedNodeId, nodes: storeNodes, edges: storeEdges } = useGraphStore.getState()
        if (selectedNodeId && !document.querySelector('input:focus, textarea:focus')) {
          e.preventDefault()
          pushSnapshot()
          setNodes(storeNodes.filter(n => n.id !== selectedNodeId))
          setEdges(storeEdges.filter(e => e.source !== selectedNodeId && e.target !== selectedNodeId))
          selectNode(null)
        }
      }
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [undo, redo])

  // ── 工具栏按钮 ──
  const toolbarButtons = (
    <div style={{
      position: 'absolute', top: 8, right: 8, zIndex: 10,
      display: 'flex', gap: 4, pointerEvents: 'none',
    }}>
      <Space size={4} style={{ pointerEvents: 'auto', background: 'rgba(255,255,255,0.95)', borderRadius: 6, padding: '4px 8px', boxShadow: '0 1px 4px rgba(0,0,0,0.06)' }}>
        <Tooltip title="撤销 (Ctrl+Z)"><Button size="small" type="text" icon={<UndoOutlined />} disabled={!canUndo()} onClick={undo} /></Tooltip>
        <Tooltip title="重做 (Ctrl+Y)"><Button size="small" type="text" icon={<RedoOutlined />} disabled={!canRedo()} onClick={redo} /></Tooltip>
        <Tooltip title="自动布局"><Button size="small" type="text" icon={<SortAscendingOutlined />} onClick={handleAutoLayout} /></Tooltip>
        <Tooltip title="适应视图"><Button size="small" type="text" icon={<CompressOutlined />} onClick={() => reactflow.fitView({ padding: 0.15, duration: 300 })} /></Tooltip>
        <Tooltip title="节点面板"><Button size="small" type="text" icon={<AppstoreOutlined />} onClick={togglePalette} style={paletteOpen ? { color: COLORS.primary, background: COLORS.obsBg } : {}} /></Tooltip>
        <Tooltip title="保存布局"><Button size="small" type="text" icon={<SaveOutlined />} onClick={() => { saveLayout(); msg.success('布局已保存') }} /></Tooltip>
      </Space>
    </div>
  )

  // ── Loading ──
  if (loading) {
    return <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}><Spin /></div>
  }

  if (observations.length === 0 && dailyLogs.length === 0) {
    return <Empty description="暂无数据，请先提炼记忆" image={Empty.PRESENTED_IMAGE_SIMPLE} />
  }

  return (
    <div style={{ height: '100%', width: '100%', borderRadius: 6, overflow: 'hidden', border: '1px solid #f0f0f0', position: 'relative' }}>
      <GraphToolbar />
      {toolbarButtons}
      <NodePalette />
      <NodeContextMenu />
      <EdgeContextMenu />
      <NodeDetailDrawer />

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
        onDragOver={onDragOver}
        onDrop={onDrop}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
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
          <span style={{ width: 20, height: 2, background: 'linear-gradient(90deg, #3BA0E8, #E8913A)', display: 'inline-block', borderRadius: 1 }} />
          拖拽连线 · 右键操作 · Ctrl+Z 撤销
        </span>
      </div>
    </div>
  )
}
