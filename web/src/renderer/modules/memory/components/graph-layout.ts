/** 自动布局工具 — 力导向简化版，用于实体关系图 */

import type { Node, Edge } from 'reactflow'

/**
 * 自动布局：按实体类型分组，高连接度的节点放中心
 */
export function autoLayout(nodes: Node[], edges: Edge[]): Node[] {
  if (nodes.length === 0) return nodes

  // 计算连接度
  const connectionCount: Record<string, number> = {}
  edges.forEach(e => {
    connectionCount[e.source] = (connectionCount[e.source] || 0) + 1
    connectionCount[e.target] = (connectionCount[e.target] || 0) + 1
  })

  // 按类型分组
  const typeOrder = ['person', 'tech', 'project', 'tool', 'concept', 'org']
  const grouped: Record<string, Node[]> = {}
  nodes.forEach(n => {
    const t = n.data?.entityType || 'concept'
    if (!grouped[t]) grouped[t] = []
    grouped[t].push(n)
  })

  const COLS = 4
  const COL_GAP = 260
  const ROW_GAP = 200
  const START_X = 80
  const START_Y = 60

  // 高连接度的排在前面
  const sortedNodes = [...nodes].sort((a, b) =>
    (connectionCount[b.id] || 0) - (connectionCount[a.id] || 0)
  )

  return sortedNodes.map((node, i) => ({
    ...node,
    position: {
      x: START_X + (i % COLS) * COL_GAP,
      y: START_Y + Math.floor(i / COLS) * ROW_GAP,
    },
  }))
}

/**
 * 自动布局并适配视图
 */
export function autoLayoutAndFit(
  nodes: Node[],
  edges: Edge[],
  setNodes: (nodes: Node[]) => void,
  fitView: (options?: any) => void,
) {
  const laid = autoLayout(nodes, edges)
  setNodes(laid)
  setTimeout(() => fitView({ padding: 0.15, duration: 400 }), 50)
}
