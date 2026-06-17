/** 记忆关系图 — React Flow 节点图（复用项目已有 reactflow v11）

功能:
  - 左侧 daily log 节点，右侧 observation 节点
  - 连线表示关联关系
  - 拖拽连线创建新关联
  - 点击连线删除关联
  - 节点可拖拽布局
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
  type OnNodesChange,
  type OnEdgesChange,
} from 'reactflow'
import 'reactflow/dist/style.css'
import { Spin, Empty, message, App, Typography } from 'antd'
import { FileTextOutlined, BulbOutlined } from '@ant-design/icons'
import {
  listObservations,
  fetchDailyLogs,
  createObservationSource,
  deleteObservationSource,
} from '../services/memory-api'
import type { Observation, MarkdownMemoryEntry } from '../services/memory-api'

const { Text } = Typography

// ── 节点样式 ────────────────────────────────────────────────

const COLORS = {
  primary: '#E8913A',
  info: '#3BA0E8',
  dailyBg: '#E6F4FF',
  dailyBorder: '#91CAFF',
  obsBg: '#FFF7ED',
  obsBorder: '#FDBA74',
  edge: '#BFBFBF',
  edgeActive: '#E8913A',
}

const CATEGORY_ICONS: Record<string, string> = {
  decisions: '🔑',
  pitfalls: '🐛',
  preferences: '👤',
  status: '📦',
}

// ── 自定义节点组件 ──────────────────────────────────────────

function DailyLogNode({ data }: { data: { title: string; wordCount: number; memoryId: string } }) {
  return (
    <div style={{
      padding: '10px 14px',
      background: COLORS.dailyBg,
      border: `1px solid ${COLORS.dailyBorder}`,
      borderRadius: 8,
      fontSize: 12,
      minWidth: 120,
      cursor: 'grab',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
        <FileTextOutlined style={{ color: COLORS.info, fontSize: 14 }} />
        <Text strong style={{ fontSize: 13 }}>{data.title}</Text>
      </div>
      <Text type="secondary" style={{ fontSize: 11 }}>{data.wordCount} 字</Text>
    </div>
  )
}

function ObservationNode({ data }: { data: { content: string; category: string; freshness: string; obsId: number } }) {
  const icon = CATEGORY_ICONS[data.category] || '📌'
  const preview = data.content.length > 60 ? data.content.slice(0, 60) + '...' : data.content
  return (
    <div style={{
      padding: '10px 14px',
      background: COLORS.obsBg,
      border: `1px solid ${COLORS.obsBorder}`,
      borderRadius: 8,
      fontSize: 12,
      minWidth: 140,
      maxWidth: 200,
      cursor: 'grab',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 4 }}>
        <span>{icon}</span>
        <Text strong style={{ fontSize: 12 }}>{preview.split('\n')[0]}</Text>
      </div>
      <Text type="secondary" style={{ fontSize: 11 }}>{data.freshness}</Text>
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
  const [loading, setLoading] = useState(true)
  const [observations, setObservations] = useState<Observation[]>([])
  const [dailyLogs, setDailyLogs] = useState<MarkdownMemoryEntry[]>([])
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])

  // ── 加载数据 ──────────────────────────────────────────

  useEffect(() => {
    loadData()
  }, [])

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

  // ── 构建图 ────────────────────────────────────────────

  const buildGraph = useCallback((obs: Observation[], logs: MarkdownMemoryEntry[]) => {
    const newNodes: Node[] = []
    const newEdges: Edge[] = []

    // Daily log 节点（左侧）
    logs.forEach((log, i) => {
      newNodes.push({
        id: `log-${log.id}`,
        type: 'dailyLog',
        position: { x: 50, y: i * 100 + 50 },
        data: { title: log.title, wordCount: log.wordCount, memoryId: log.id },
      })
    })

    // Observation 节点（右侧）
    obs.forEach((ob, i) => {
      newNodes.push({
        id: `obs-${ob.id}`,
        type: 'observation',
        position: { x: 450, y: i * 120 + 50 },
        data: { content: ob.content, category: ob.category, freshness: ob.freshness, obsId: ob.id },
      })

      // 连线（关联关系）
      if (ob.sources) {
        ob.sources.forEach(src => {
          const sourceLogExists = logs.some(l => l.id === String(src.logId))
          if (sourceLogExists) {
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

  // ── 连线回调（创建关联）──────────────────────────────

  const onConnect: OnConnect = useCallback(async (connection: Connection) => {
    if (!connection.source || !connection.target) return

    // 只允许 dailyLog → observation 方向
    if (!connection.source.startsWith('log-') || !connection.target.startsWith('obs-')) {
      msg.warning('只能从日志拖拽到提炼记忆')
      return
    }

    const logId = parseInt(connection.source.replace('log-', ''))
    const obsId = parseInt(connection.target.replace('obs-', ''))

    // 乐观更新
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
      // 替换临时边为真实边
      setEdges(eds => eds.map(e =>
        e.id === tempEdgeId
          ? { ...e, id: `edge-${result.id}`, animated: false, style: { stroke: COLORS.edge, strokeWidth: 2 }, markerEnd: { type: MarkerType.ArrowClosed, color: COLORS.edge } }
          : e
      ))
      msg.success('关联创建成功')
    } catch {
      // 回滚
      setEdges(eds => eds.filter(e => e.id !== tempEdgeId))
      msg.error('关联创建失败')
    }
  }, [])

  // ── 点击边删除关联 ───────────────────────────────────

  const onEdgeClick = useCallback(async (_: React.MouseEvent, edge: Edge) => {
    const sourceId = edge.data?.sourceId
    if (!sourceId) return

    // 乐观删除
    setEdges(eds => eds.filter(e => e.id !== edge.id))

    try {
      await deleteObservationSource(sourceId)
      msg.success('关联已删除')
    } catch {
      // 回滚
      setEdges(eds => [...eds, edge])
      msg.error('删除失败')
    }
  }, [])

  // ── Loading ───────────────────────────────────────────

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
        <Spin />
      </div>
    )
  }

  if (observations.length === 0 && dailyLogs.length === 0) {
    return (
      <Empty
        description="暂无数据，请先提炼记忆"
        image={Empty.PRESENTED_IMAGE_SIMPLE}
      />
    )
  }

  return (
    <div style={{ height: '100%', width: '100%', borderRadius: 8, overflow: 'hidden', border: '1px solid #f0f0f0' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onEdgeClick={onEdgeClick}
        nodeTypes={nodeTypes}
        fitView
        attributionPosition="bottom-left"
        style={{ background: '#fafafa' }}
      >
        <Controls />
        <MiniMap
          nodeColor={(node) => node.type === 'dailyLog' ? COLORS.dailyBg : COLORS.obsBg}
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
          关联（点击删除）
        </span>
      </div>
    </div>
  )
}
