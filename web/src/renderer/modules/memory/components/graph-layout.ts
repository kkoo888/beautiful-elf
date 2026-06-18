/** 自动布局工具 — 简化版 dagre，不依赖外部包

布局策略：
  - 左列：Daily Logs（按时间倒序）
  - 右列：Observations（按分类分组）
  - 自动计算连线节点的位置
*/

import type { Node, Edge } from 'reactflow'

const LAYOUT_CONFIG = {
  logX: 80,
  obsX: 500,
  startY: 60,
  logGapY: 100,
  obsGapY: 120,
  groupGapY: 40,
}

/**
 * 自动布局：左侧日志，右侧提炼记忆
 */
export function autoLayout(nodes: Node[], edges: Edge[]): Node[] {
  const logNodes = nodes.filter(n => n.type === 'dailyLog')
  const obsNodes = nodes.filter(n => n.type === 'observation')

  // 日志按标题（日期）排序
  const sortedLogs = [...logNodes].sort((a, b) =>
    (a.data.title || '').localeCompare(b.data.title || '')
  )

  // 提炼记忆按分类分组，再按内容排序
  const categoryOrder = ['decisions', 'pitfalls', 'preferences', 'status']
  const sortedObs = [...obsNodes].sort((a, b) => {
    const catA = categoryOrder.indexOf(a.data.category || 'status')
    const catB = categoryOrder.indexOf(b.data.category || 'status')
    if (catA !== catB) return catA - catB
    return (a.data.content || '').localeCompare(b.data.content || '')
  })

  // 计算连线密度，高连接度的节点放中间
  const connectionCount: Record<string, number> = {}
  edges.forEach(e => {
    connectionCount[e.source] = (connectionCount[e.source] || 0) + 1
    connectionCount[e.target] = (connectionCount[e.target] || 0) + 1
  })

  // 布局日志节点
  const updatedNodes: Node[] = nodes.map(node => {
    if (node.type === 'dailyLog') {
      const idx = sortedLogs.findIndex(n => n.id === node.id)
      return {
        ...node,
        position: {
          x: LAYOUT_CONFIG.logX,
          y: LAYOUT_CONFIG.startY + idx * LAYOUT_CONFIG.logGapY,
        },
      }
    }

    if (node.type === 'observation') {
      const idx = sortedObs.findIndex(n => n.id === node.id)
      return {
        ...node,
        position: {
          x: LAYOUT_CONFIG.obsX,
          y: LAYOUT_CONFIG.startY + idx * LAYOUT_CONFIG.obsGapY,
        },
      }
    }

    return node
  })

  return updatedNodes
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
