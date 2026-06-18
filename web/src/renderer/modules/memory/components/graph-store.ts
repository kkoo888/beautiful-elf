/** 记忆关系图 Zustand Store — 对标 Dify store 分层设计 */

import { create } from 'zustand'
import type { Node, Edge } from 'reactflow'
import type { Observation, MarkdownMemoryEntry } from '../services/memory-api'

// ── 状态类型 ──────────────────────────────────────────────

interface GraphState {
  // 数据
  observations: Observation[]
  dailyLogs: MarkdownMemoryEntry[]

  // React Flow 状态
  nodes: Node[]
  edges: Edge[]

  // UI 状态
  selectedNodeId: string | null
  contextMenu: { nodeId: string; x: number; y: number } | null
  edgeContextMenu: { edgeId: string; x: number; y: number } | null
  detailDrawerOpen: boolean
  searchKeyword: string
  categoryFilter: string
  loading: boolean

  // Actions
  setObservations: (obs: Observation[]) => void
  setDailyLogs: (logs: MarkdownMemoryEntry[]) => void
  setNodes: (nodes: Node[]) => void
  setEdges: (edges: Edge[]) => void
  selectNode: (nodeId: string | null) => void
  openContextMenu: (nodeId: string, x: number, y: number) => void
  closeContextMenu: () => void
  openEdgeContextMenu: (edgeId: string, x: number, y: number) => void
  closeEdgeContextMenu: () => void
  openDetailDrawer: () => void
  closeDetailDrawer: () => void
  setSearchKeyword: (keyword: string) => void
  setCategoryFilter: (filter: string) => void
  setLoading: (loading: boolean) => void

  // 派生
  getSelectedNode: () => Node | null
  getFilteredNodes: () => Node[]
}

export const useGraphStore = create<GraphState>((set, get) => ({
  // 初始状态
  observations: [],
  dailyLogs: [],
  nodes: [],
  edges: [],
  selectedNodeId: null,
  contextMenu: null,
  edgeContextMenu: null,
  detailDrawerOpen: false,
  searchKeyword: '',
  categoryFilter: 'all',
  loading: true,

  // Actions
  setObservations: (observations) => set({ observations }),
  setDailyLogs: (dailyLogs) => set({ dailyLogs }),
  setNodes: (nodes) => set({ nodes }),
  setEdges: (edges) => set({ edges }),

  selectNode: (nodeId) => set({ selectedNodeId: nodeId, detailDrawerOpen: nodeId !== null }),

  openContextMenu: (nodeId, x, y) => set({ contextMenu: { nodeId, x, y } }),
  closeContextMenu: () => set({ contextMenu: null }),

  openEdgeContextMenu: (edgeId, x, y) => set({ edgeContextMenu: { edgeId, x, y } }),
  closeEdgeContextMenu: () => set({ edgeContextMenu: null }),

  openDetailDrawer: () => set({ detailDrawerOpen: true }),
  closeDetailDrawer: () => set({ detailDrawerOpen: false, selectedNodeId: null }),

  setSearchKeyword: (searchKeyword) => set({ searchKeyword }),
  setCategoryFilter: (categoryFilter) => set({ categoryFilter }),
  setLoading: (loading) => set({ loading }),

  // 派生
  getSelectedNode: () => {
    const { nodes, selectedNodeId } = get()
    return nodes.find(n => n.id === selectedNodeId) ?? null
  },

  getFilteredNodes: () => {
    const { nodes, searchKeyword, categoryFilter } = get()
    return nodes.map(node => {
      let visible = true

      // 搜索过滤
      if (searchKeyword) {
        const kw = searchKeyword.toLowerCase()
        const content = (node.data.content || node.data.title || '').toLowerCase()
        visible = content.includes(kw)
      }

      // 分类过滤
      if (visible && categoryFilter !== 'all' && node.type === 'observation') {
        visible = node.data.category === categoryFilter
      }

      return { ...node, hidden: !visible }
    })
  },
}))
