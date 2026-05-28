/** DAG 可视化编辑器（React Flow） */

import { useCallback, useMemo, useRef } from 'react'
import ReactFlow, {
  Controls,
  Background,
  MiniMap,
  addEdge,
  useNodesState,
  useEdgesState,
  BackgroundVariant,
  type Connection,
  type Edge,
  type Node,
  type OnConnect,
  type OnNodesChange,
  type OnEdgesChange,
  type NodeTypes,
} from 'reactflow'
import 'reactflow/dist/style.css'
import {} from 'antd'
import {
  StartNode,
  EndNode,
  TaskNode,
  ConditionNode,
  ParallelNode,
  NODE_STATUS_STYLES,
} from './nodes'
import type { WorkflowNode, WorkflowEdge, DagNodeType, NodeStatus } from '../types/workflow'

// ─── 节点类型注册 ──────────────────────────────────────────

const nodeTypes: NodeTypes = {
  start: StartNode,
  end: EndNode,
  task: TaskNode,
  condition: ConditionNode,
  parallel: ParallelNode,
}

// ─── 工具函数：WorkflowNode ↔ ReactFlow Node ─────────────

function toRFNode(wfNode: WorkflowNode): Node {
  return {
    id: wfNode.id,
    type: wfNode.type,
    position: wfNode.position,
    data: { label: wfNode.label, status: wfNode.status, ...wfNode.config },
  }
}

function toRFEdge(wfEdge: WorkflowEdge): Edge {
  return {
    id: wfEdge.id,
    source: wfEdge.source,
    target: wfEdge.target,
    label: wfEdge.label,
    animated: false,
    style: { stroke: '#8c8c8c', strokeWidth: 2 },
  }
}

function fromRFNode(rfNode: Node): WorkflowNode {
  const { label, status, ...rest } = rfNode.data ?? {}
  return {
    id: rfNode.id,
    type: (rfNode.type ?? 'task') as DagNodeType,
    label: label ?? '',
    position: rfNode.position,
    config: rest ?? {},
    status: (status ?? 'idle') as NodeStatus,
  }
}

function fromRFEdge(rfEdge: Edge): WorkflowEdge {
  return {
    id: rfEdge.id,
    source: rfEdge.source,
    target: rfEdge.target,
    label: typeof rfEdge.label === 'string' ? rfEdge.label : undefined,
  }
}

// ─── 组件 Props ────────────────────────────────────────────

interface WorkflowEditorProps {
  /** 工作流节点 */
  nodes: WorkflowNode[]
  /** 工作流边 */
  edges: WorkflowEdge[]
  /** 节点变更回调 */
  onNodesChange: (nodes: WorkflowNode[]) => void
  /** 边变更回调 */
  onEdgesChange: (edges: WorkflowEdge[]) => void
  /** 选中节点回调 */
  onNodeSelect?: (node: WorkflowNode | null) => void
  /** 是否只读 */
  readonly?: boolean
}

/** 节点类型标签映射 */
const NODE_TYPE_LABEL: Record<DagNodeType, { label: string; color: string }> = {
  start: { label: '开始', color: 'green' },
  end: { label: '结束', color: 'red' },
  task: { label: '任务', color: 'blue' },
  condition: { label: '条件', color: 'orange' },
  parallel: { label: '并行', color: 'purple' },
}

export function WorkflowEditor({
  nodes: wfNodes,
  edges: wfEdges,
  onNodesChange: onWfNodesChange,
  onEdgesChange: onWfEdgesChange,
  onNodeSelect,
  readonly = false,
}: WorkflowEditorProps) {
  const reactFlowWrapper = useRef<HTMLDivElement>(null)

  // 转换为 React Flow 格式
  const initialNodes = useMemo(() => wfNodes.map(toRFNode), [wfNodes])
  const initialEdges = useMemo(() => wfEdges.map(toRFEdge), [wfEdges])

  const [nodes, setNodes, onNodesChangeRaw] = useNodesState(initialNodes)
  const [edges, setEdges, onEdgesChangeRaw] = useEdgesState(initialEdges)

  // 同步外部数据变更
  useMemo(() => {
    setNodes(wfNodes.map(toRFNode))
  }, [wfNodes, setNodes])

  useMemo(() => {
    setEdges(wfEdges.map(toRFEdge))
  }, [wfEdges, setEdges])

  // 节点变更 → 同步回父组件
  const handleNodesChange: OnNodesChange = useCallback(
    (changes) => {
      onNodesChangeRaw(changes)
      // 延迟同步：在 React Flow 状态更新后读取最新值
      setTimeout(() => {
        setNodes((nds) => {
          onWfNodesChange(nds.map(fromRFNode))
          return nds
        })
      }, 0)
    },
    [onNodesChangeRaw, onWfNodesChange, setNodes]
  )

  // 边变更 → 同步回父组件
  const handleEdgesChange: OnEdgesChange = useCallback(
    (changes) => {
      onEdgesChangeRaw(changes)
      setTimeout(() => {
        setEdges((eds) => {
          onWfEdgesChange(eds.map(fromRFEdge))
          return eds
        })
      }, 0)
    },
    [onEdgesChangeRaw, onWfEdgesChange, setEdges]
  )

  // 连线
  const onConnect: OnConnect = useCallback(
    (connection: Connection) => {
      if (readonly) return
      const newEdge: Edge = {
        ...connection,
        id: `e-${connection.source}-${connection.target}`,
        animated: false,
        style: { stroke: '#8c8c8c', strokeWidth: 2 },
      }
      setEdges((eds) => addEdge(newEdge, eds))
      setTimeout(() => {
        setEdges((eds) => {
          onWfEdgesChange(eds.map(fromRFEdge))
          return eds
        })
      }, 0)
    },
    [readonly, setEdges, onWfEdgesChange]
  )

  // 节点选中
  const handleNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      onNodeSelect?.(fromRFNode(node))
    },
    [onNodeSelect]
  )

  // 点击空白取消选中
  const handlePaneClick = useCallback(() => {
    onNodeSelect?.(null)
  }, [onNodeSelect])

  // MiniMap 节点颜色
  const minimapNodeColor = useCallback((node: Node) => {
    const status = (node.data?.status as string) ?? 'idle'
    const style = NODE_STATUS_STYLES[status] ?? NODE_STATUS_STYLES.idle
    return style.border
  }, [])

  // 拖拽添加节点
  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault()
    event.dataTransfer.dropEffect = 'move'
  }, [])

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault()
      if (readonly) return

      const type = event.dataTransfer.getData('application/reactflow-type') as DagNodeType
      const label = event.dataTransfer.getData('application/reactflow-label')
      if (!type || !label) return

      const bounds = reactFlowWrapper.current?.getBoundingClientRect()
      if (!bounds) return

      const position = {
        x: event.clientX - bounds.left - 60,
        y: event.clientY - bounds.top - 20,
      }

      const newNode: WorkflowNode = {
        id: `node-${Date.now()}`,
        type,
        label,
        position,
        config: {},
        status: 'idle',
      }

      const updatedNodes = [...wfNodes, newNode]
      onWfNodesChange(updatedNodes)
    },
    [readonly, wfNodes, onWfNodesChange]
  )

  return (
    <div ref={reactFlowWrapper} style={{ width: '100%', height: '100%' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={handleNodesChange}
        onEdgesChange={handleEdgesChange}
        onConnect={onConnect}
        onNodeClick={handleNodeClick}
        onPaneClick={handlePaneClick}
        onDragOver={onDragOver}
        onDrop={onDrop}
        nodeTypes={nodeTypes}
        fitView
        snapToGrid
        snapGrid={[16, 16]}
        nodesDraggable={!readonly}
        nodesConnectable={!readonly}
        elementsSelectable={!readonly}
        deleteKeyCode={readonly ? null : 'Delete'}
        proOptions={{ hideAttribution: true }}
      >
        <Controls position="bottom-left" />
        <Background variant={BackgroundVariant.Dots} gap={16} size={1} color="#e0e0e0" />
        <MiniMap nodeColor={minimapNodeColor} position="bottom-right" pannable zoomable />
      </ReactFlow>
    </div>
  )
}

// ─── 导出节点类型标签（供配置面板使用） ─────────────────────

export { NODE_TYPE_LABEL }
