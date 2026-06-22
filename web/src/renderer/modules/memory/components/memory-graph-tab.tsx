/** 实体关系图 — 显示实体节点与实体间的关系

功能：
  - 实体节点（按类型着色：person/tech/project/tool/concept/org）
  - 关系连线（渐变色 + 关系类型标签）
  - 搜索 + 类型筛选
  - 撤销/重做、自动布局、布局持久化
  - 右键菜单、详情抽屉
  - 拖拽添加节点
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
  BaseEdge,
  EdgeLabelRenderer,
  getBezierPath,
} from 'reactflow'
import 'reactflow/dist/style.css'
import { Spin, Empty, App, Tooltip, Button, Space } from 'antd'
import {
  UndoOutlined, RedoOutlined,
  AppstoreOutlined, SortAscendingOutlined,
  SaveOutlined, CompressOutlined,
} from '@ant-design/icons'
import {
  getEntityGraph,
  createRelation,
  deleteRelation,
} from '../services/memory-entity-api'
import { useGraphStore } from './graph-store'
import { NodeContextMenu, EdgeContextMenu } from './graph-context-menu'
import { NodeDetailDrawer } from './graph-detail-drawer'
import { GraphToolbar } from './graph-toolbar'
import { NodePalette } from './graph-palette'
import { autoLayoutAndFit } from './graph-layout'

// ── 样式常量 ──────────────────────────────────────────────

const ENTITY_COLORS: Record<string, { bg: string; border: string; selected: string; text: string }> = {
  person:  { bg: '#E6F4FF', border: '#91CAFF', selected: '#1890ff', text: '#1890ff' },
  tech:    { bg: '#E6FFFB', border: '#87E8DE', selected: '#13C2C2', text: '#13C2C2' },
  project: { bg: '#F9F0FF', border: '#D3ADF7', selected: '#722ED1', text: '#722ED1' },
  tool:    { bg: '#F6FFED', border: '#B7EB8F', selected: '#52C41A', text: '#52C41A' },
  concept: { bg: '#FFF7E6', border: '#FFD591', selected: '#FA8C16', text: '#FA8C16' },
  org:     { bg: '#F0F5FF', border: '#ADC6FF', selected: '#2F54EB', text: '#2F54EB' },
}
const DEFAULT_COLOR = { bg: '#FAFAFA', border: '#D9D9D9', selected: '#8c8c8c', text: '#8c8c8c' }

const ENTITY_TYPE_LABEL: Record<string, string> = {
  person: '人物', tech: '技术', project: '项目',
  tool: '工具', concept: '概念', org: '组织',
}

const ENTITY_TYPE_ICON: Record<string, string> = {
  person: '👤', tech: '🛠', project: '📁',
  tool: '🔧', concept: '💡', org: '🏢',
}

const RELATION_LABEL: Record<string, string> = {
  uses: '使用', depends: '依赖', belongs: '属于',
  creates: '创建', works_at: '就职于', related: '相关',
  causes: '导致', enables: '使能', prevents: '阻止',
}

// ── 实体节点组件 ──────────────────────────────────────────

function EntityNode({ data, selected }: { data: any; selected?: boolean }) {
  const searchKeyword = useGraphStore(s => s.searchKeyword)
  const entityTypeFilter = useGraphStore(s => s.entityTypeFilter)
  const dimmedBySearch = searchKeyword && !(data.name || '').toLowerCase().includes(searchKeyword.toLowerCase())
  const dimmedByType = entityTypeFilter !== 'all' && data.entityType !== entityTypeFilter
  const dimmed = dimmedBySearch || dimmedByType

  const colors = ENTITY_COLORS[data.entityType] || DEFAULT_COLOR
  const icon = ENTITY_TYPE_ICON[data.entityType] || '📌'
  const typeLabel = ENTITY_TYPE_LABEL[data.entityType] || data.entityType

  return (
    <div style={{
      padding: 0, borderRadius: 8, overflow: 'hidden',
      border: `2px solid ${selected ? colors.selected : colors.border}`,
      background: selected ? colors.bg : '#fff',
      opacity: dimmed ? 0.15 : 1,
      transition: 'opacity 0.2s, border-color 0.15s, box-shadow 0.15s',
      boxShadow: selected ? `0 0 0 3px ${colors.selected}22` : '0 1px 4px rgba(0,0,0,0.06)',
      minWidth: 160, maxWidth: 220,
    }}>
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 6,
        padding: '8px 12px', background: colors.bg,
      }}>
        <span style={{ fontSize: 14 }}>{icon}</span>
        <span style={{ fontSize: 10, padding: '1px 6px', borderRadius: 4, background: '#fff', color: colors.text, fontWeight: 500 }}>
          {typeLabel}
        </span>
      </div>
      {/* Body */}
      <div style={{ padding: '8px 12px' }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: '#1a1a2e', lineHeight: 1.4, wordBreak: 'break-all' }}>
          {data.name}
        </div>
        {data.description && (
          <div style={{ fontSize: 11, color: '#8c8c8c', marginTop: 4, lineHeight: 1.5, overflow: 'hidden', textOverflow: 'ellipsis', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' }}>
            {data.description}
          </div>
        )}
      </div>
      {/* Footer */}
      <div style={{
        padding: '4px 12px 6px', fontSize: 11, color: '#bfbfbf',
        borderTop: '1px solid #f0f0f0',
      }}>
        提及 {data.mentionCount ?? 0} 次
      </div>
    </div>
  )
}

const nodeTypes = { entity: EntityNode }

// ── 带标签的渐变连线 ──────────────────────────────────────

function RelationEdge({ id, sourceX, sourceY, targetX, targetY, style, markerEnd, data, label }: any) {
  const [edgePath, labelX, labelY] = getBezierPath({ sourceX, sourceY, targetX, targetY })
  const gradientId = `gradient-${id}`

  return (
    <>
      <defs>
        <linearGradient id={gradientId} x1={sourceX} y1={sourceY} x2={targetX} y2={targetY} gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#3BA0E8" stopOpacity={0.7} />
          <stop offset="100%" stopColor="#E8913A" stopOpacity={0.8} />
        </linearGradient>
      </defs>
      <BaseEdge path={edgePath} markerEnd={markerEnd} style={{ ...style, stroke: `url(#${gradientId})`, strokeWidth: 2 }} />
      {label && (
        <EdgeLabelRenderer>
          <div style={{
            position: 'absolute',
            transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
            pointerEvents: 'all',
            fontSize: 10,
            fontWeight: 500,
            color: '#8c8c8c',
            background: 'rgba(255,255,255,0.9)',
            padding: '1px 6px',
            borderRadius: 4,
            border: '1px solid #f0f0f0',
            whiteSpace: 'nowrap',
          }}>
            {label}
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  )
}

const edgeTypes = { relation: RelationEdge }

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
    setEntities, setRelations,
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
      const graphData = await getEntityGraph()
      setEntities(graphData.nodes.map(n => ({
        id: parseInt(n.id.replace('entity-', '')),
        name: n.name,
        entityType: n.type as any,
        description: n.description,
        aliases: '',
        mentionCount: n.mentionCount,
        lastMentionedAt: '',
      })))
      setRelations(graphData.edges.map(e => ({
        id: parseInt(e.id.replace('rel-', '')),
        sourceEntityId: parseInt(e.source.replace('entity-', '')),
        targetEntityId: parseInt(e.target.replace('entity-', '')),
        relationType: e.type as any,
        weight: e.weight,
        evidence: '',
        sourceObsId: 0,
      })))
      buildGraph(graphData)
    } catch { msg.error('加载实体图失败') } finally {
      setLoading(false)
    }
  }, [])

  const buildGraph = useCallback((graphData: { nodes: any[]; edges: any[] }) => {
    const newNodes: Node[] = graphData.nodes.map((n, i) => ({
      id: n.id,
      type: 'entity',
      position: { x: (i % 4) * 250 + 50, y: Math.floor(i / 4) * 180 + 50 },
      data: {
        name: n.name,
        entityType: n.type,
        description: n.description,
        mentionCount: n.mentionCount,
        entityId: parseInt(n.id.replace('entity-', '')),
      },
    }))

    const newEdges: Edge[] = graphData.edges.map(e => ({
      id: e.id,
      source: e.source,
      target: e.target,
      type: 'relation',
      animated: false,
      markerEnd: { type: MarkerType.ArrowClosed, color: '#E8913A' },
      label: RELATION_LABEL[e.type] || e.type,
      data: { relationType: e.type, weight: e.weight, relationId: parseInt(e.id.replace('rel-', '')) },
    }))

    setNodes(newNodes)
    setEdges(newEdges)
  }, [])

  // ── 连线（创建实体间关系）──
  const onConnect: OnConnect = useCallback(async (connection: Connection) => {
    if (!connection.source || !connection.target) return
    if (connection.source === connection.target) return

    pushSnapshot()

    const sourceEntityId = parseInt(connection.source.replace('entity-', ''))
    const targetEntityId = parseInt(connection.target.replace('entity-', ''))
    if (isNaN(sourceEntityId) || isNaN(targetEntityId)) return

    const tempEdgeId = `edge-temp-${Date.now()}`
    setEdges(eds => addEdge({
      ...connection,
      id: tempEdgeId,
      type: 'relation',
      animated: true,
      label: '相关',
      markerEnd: { type: MarkerType.ArrowClosed, color: '#E8913A' },
    }, eds))

    try {
      const result = await createRelation({ sourceEntityId, targetEntityId, relationType: 'related' })
      setEdges(eds => eds.map(e =>
        e.id === tempEdgeId
          ? { ...e, id: `rel-${result.id}`, animated: false, label: RELATION_LABEL[result.relationType] || result.relationType, data: { relationType: result.relationType, weight: result.weight, relationId: result.id } }
          : e
      ))
      msg.success('关系创建成功')
    } catch {
      setEdges(eds => eds.filter(e => e.id !== tempEdgeId))
      msg.error('关系创建失败')
    }
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
    const relationId = edge.data?.relationId
    pushSnapshot()
    setEdges(eds => eds.filter(e => e.id !== edge.id))
    if (relationId) {
      try { await deleteRelation(relationId) } catch {}
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
      id: `entity-new-${Date.now()}`,
      type: 'entity',
      position,
      data: { name: `新${ENTITY_TYPE_LABEL[type] || '实体'}`, entityType: type, description: '', mentionCount: 0, entityId: 0 },
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
      if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey) {
        e.preventDefault()
        undo()
      }
      if ((e.ctrlKey || e.metaKey) && (e.key === 'y' || (e.key === 'z' && e.shiftKey))) {
        e.preventDefault()
        redo()
      }
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
        <Tooltip title="节点面板"><Button size="small" type="text" icon={<AppstoreOutlined />} onClick={togglePalette} style={paletteOpen ? { color: '#E8913A', background: '#FFF7ED' } : {}} /></Tooltip>
        <Tooltip title="保存布局"><Button size="small" type="text" icon={<SaveOutlined />} onClick={() => { saveLayout(); msg.success('布局已保存') }} /></Tooltip>
      </Space>
    </div>
  )

  // ── Loading ──
  if (loading) {
    return <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}><Spin /></div>
  }

  if (nodes.length === 0) {
    return <Empty description="暂无实体，请先在「实体」Tab 创建实体" image={Empty.PRESENTED_IMAGE_SIMPLE} />
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
          nodeColor={node => {
            const t = node.data?.entityType
            return ENTITY_COLORS[t]?.bg || '#FAFAFA'
          }}
          maskColor="rgba(0,0,0,0.08)"
          style={{ border: '1px solid #f0f0f0', borderRadius: 4 }}
        />
        <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="#e8e8e8" />
      </ReactFlow>

      {/* 图例 */}
      <div style={{
        position: 'absolute', bottom: 12, left: 12,
        display: 'flex', gap: 12, flexWrap: 'wrap',
        padding: '6px 12px',
        background: 'rgba(255,255,255,0.9)', borderRadius: 6,
        border: '1px solid #f0f0f0', fontSize: 11,
      }}>
        {Object.entries(ENTITY_TYPE_LABEL).map(([type, label]) => {
          const c = ENTITY_COLORS[type]
          return (
            <span key={type} style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
              <span style={{ width: 10, height: 10, background: c.bg, border: `1px solid ${c.border}`, borderRadius: 3, display: 'inline-block' }} />
              {label}
            </span>
          )
        })}
        <span style={{ display: 'flex', alignItems: 'center', gap: 3, marginLeft: 4 }}>
          <span style={{ width: 16, height: 2, background: 'linear-gradient(90deg, #3BA0E8, #E8913A)', display: 'inline-block', borderRadius: 1 }} />
          关系
        </span>
      </div>
    </div>
  )
}
