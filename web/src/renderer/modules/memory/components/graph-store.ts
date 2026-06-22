/** 记忆关系图 Zustand Store — 实体关系图版本

增强功能：
  - 撤销/重做（手动实现 temporal，不依赖 zundo）
  - 布局持久化（localStorage）
  - 状态分片管理
*/

import { create } from 'zustand'
import type { Node, Edge } from 'reactflow'
import type { MemoryEntity, EntityRelation } from '../services/memory-entity-api'

// ── 历史快照 ──────────────────────────────────────────────

interface Snapshot {
  nodes: Node[]
  edges: Edge[]
}

const MAX_HISTORY = 50
const STORAGE_KEY = 'memory-entity-graph-layout'

// ── 状态类型 ──────────────────────────────────────────────

interface GraphState {
  // 数据
  entities: MemoryEntity[]
  relations: EntityRelation[]

  // React Flow 状态
  nodes: Node[]
  edges: Edge[]

  // UI 状态
  selectedNodeId: string | null
  contextMenu: { nodeId: string; x: number; y: number } | null
  edgeContextMenu: { edgeId: string; x: number; y: number } | null
  detailDrawerOpen: boolean
  searchKeyword: string
  entityTypeFilter: string
  loading: boolean
  paletteOpen: boolean

  // 撤销/重做
  past: Snapshot[]
  future: Snapshot[]

  // Actions - 数据
  setEntities: (entities: MemoryEntity[]) => void
  setRelations: (relations: EntityRelation[]) => void

  // Actions - 节点/边（带历史记录）
  setNodes: (nodes: Node[], skipHistory?: boolean) => void
  setEdges: (edges: Edge[], skipHistory?: boolean) => void
  pushSnapshot: () => void
  undo: () => void
  redo: () => void
  canUndo: () => boolean
  canRedo: () => boolean

  // Actions - UI
  selectNode: (nodeId: string | null) => void
  openContextMenu: (nodeId: string, x: number, y: number) => void
  closeContextMenu: () => void
  openEdgeContextMenu: (edgeId: string, x: number, y: number) => void
  closeEdgeContextMenu: () => void
  openDetailDrawer: () => void
  closeDetailDrawer: () => void
  setSearchKeyword: (keyword: string) => void
  setEntityTypeFilter: (filter: string) => void
  setLoading: (loading: boolean) => void
  togglePalette: () => void
  setPaletteOpen: (open: boolean) => void

  // Actions - 持久化
  saveLayout: () => void
  loadLayout: () => { nodes: Node[]; edges: Edge[] } | null
  clearLayout: () => void
}

export const useGraphStore = create<GraphState>((set, get) => ({
  // 初始状态
  entities: [],
  relations: [],
  nodes: [],
  edges: [],
  selectedNodeId: null,
  contextMenu: null,
  edgeContextMenu: null,
  detailDrawerOpen: false,
  searchKeyword: '',
  entityTypeFilter: 'all',
  loading: true,
  paletteOpen: false,
  past: [],
  future: [],

  // 数据
  setEntities: (entities) => set({ entities }),
  setRelations: (relations) => set({ relations }),

  // 节点/边（带历史）
  setNodes: (nodes, skipHistory = false) => {
    const state = get()
    if (!skipHistory) {
      const snapshot: Snapshot = { nodes: state.nodes, edges: state.edges }
      const past = [...state.past, snapshot].slice(-MAX_HISTORY)
      set({ nodes, past, future: [] })
    } else {
      set({ nodes })
    }
  },

  setEdges: (edges, skipHistory = false) => {
    const state = get()
    if (!skipHistory) {
      const snapshot: Snapshot = { nodes: state.nodes, edges: state.edges }
      const past = [...state.past, snapshot].slice(-MAX_HISTORY)
      set({ edges, past, future: [] })
    } else {
      set({ edges })
    }
  },

  pushSnapshot: () => {
    const { nodes, edges, past } = get()
    const snapshot: Snapshot = { nodes: [...nodes], edges: [...edges] }
    set({ past: [...past, snapshot].slice(-MAX_HISTORY), future: [] })
  },

  undo: () => {
    const { past, nodes, edges } = get()
    if (past.length === 0) return
    const prev = past[past.length - 1]
    const current: Snapshot = { nodes, edges }
    set({
      nodes: prev.nodes,
      edges: prev.edges,
      past: past.slice(0, -1),
      future: [current, ...get().future],
    })
  },

  redo: () => {
    const { future, nodes, edges } = get()
    if (future.length === 0) return
    const next = future[0]
    const current: Snapshot = { nodes, edges }
    set({
      nodes: next.nodes,
      edges: next.edges,
      past: [...get().past, current],
      future: future.slice(1),
    })
  },

  canUndo: () => get().past.length > 0,
  canRedo: () => get().future.length > 0,

  // UI
  selectNode: (nodeId) => set({ selectedNodeId: nodeId, detailDrawerOpen: nodeId !== null }),
  openContextMenu: (nodeId, x, y) => set({ contextMenu: { nodeId, x, y } }),
  closeContextMenu: () => set({ contextMenu: null }),
  openEdgeContextMenu: (edgeId, x, y) => set({ edgeContextMenu: { edgeId, x, y } }),
  closeEdgeContextMenu: () => set({ edgeContextMenu: null }),
  openDetailDrawer: () => set({ detailDrawerOpen: true }),
  closeDetailDrawer: () => set({ detailDrawerOpen: false, selectedNodeId: null }),
  setSearchKeyword: (searchKeyword) => set({ searchKeyword }),
  setEntityTypeFilter: (entityTypeFilter) => set({ entityTypeFilter }),
  setLoading: (loading) => set({ loading }),
  togglePalette: () => set(s => ({ paletteOpen: !s.paletteOpen })),
  setPaletteOpen: (paletteOpen) => set({ paletteOpen }),

  // 持久化
  saveLayout: () => {
    const { nodes, edges } = get()
    try {
      const data = JSON.stringify({ nodes, edges, savedAt: Date.now() })
      localStorage.setItem(STORAGE_KEY, data)
    } catch {}
  },

  loadLayout: () => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      if (!raw) return null
      const data = JSON.parse(raw)
      return { nodes: data.nodes || [], edges: data.edges || [] }
    } catch { return null }
  },

  clearLayout: () => {
    try { localStorage.removeItem(STORAGE_KEY) } catch {}
  },
}))
