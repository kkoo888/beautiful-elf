import { useState, useCallback, useEffect, useRef } from 'react'
import { message } from 'antd'
import { useDebounce } from '@/hooks'
import type { ClipboardItem, ClipboardContentType } from '../types/clipboard'
import {
  fetchClipboardList,
  deleteClipboardItem,
  togglePinClipboardItem
} from '../services/clipboard-api'

/** 剪贴板状态 */
interface ClipboardState {
  /** 全部列表（含固定项） */
  items: ClipboardItem[]
  /** 加载中 */
  loading: boolean
  /** 搜索关键词（原始值，未经防抖） */
  keyword: string
  /** 当前选中查看详情的条目 */
  detailItem: ClipboardItem | null
  /** 右键菜单锚点条目 */
  contextMenuItem: ClipboardItem | null
  /** 右键菜单位置 */
  contextMenuPosition: { x: number; y: number } | null
  /** 当前页码 */
  page: number
  /** 是否有更多数据 */
  hasMore: boolean
}

/**
 * 剪贴板模块状态管理 Hook
 */
export function useClipboard() {
  const [state, setState] = useState<ClipboardState>({
    items: [],
    loading: false,
    keyword: '',
    detailItem: null,
    contextMenuItem: null,
    contextMenuPosition: null,
    page: 1,
    hasMore: true
  })

  const debouncedKeyword = useDebounce(state.keyword, 300)
  const isInitialMount = useRef(true)

  // ============================================================
  // 数据加载
  // ============================================================

  const loadItems = useCallback(
    async (reset = false) => {
      setState((s) => ({ ...s, loading: true }))
      try {
        const page = reset ? 1 : state.page
        const res = await fetchClipboardList({
          page,
          pageSize: 50,
          keyword: debouncedKeyword || undefined
        })

        setState((s) => ({
          ...s,
          items: reset ? res.items : [...s.items, ...res.items],
          loading: false,
          page,
          hasMore: s.items.length + res.items.length < res.total
        }))
      } catch {
        setState((s) => ({ ...s, loading: false }))
        message.error('加载剪贴板历史失败')
      }
    },
    [debouncedKeyword, state.page]
  )

  // 首次加载 & 搜索词变化时重新加载
  useEffect(() => {
    if (isInitialMount.current) {
      isInitialMount.current = false
    }
    setState((s) => ({ ...s, page: 1 }))
    loadItems(true)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedKeyword])

  // ============================================================
  // 操作
  // ============================================================

  /** 设置搜索关键词 */
  const setKeyword = useCallback((keyword: string) => {
    setState((s) => ({ ...s, keyword }))
  }, [])

  /** 一键复制到系统剪贴板 */
  const copyToClipboard = useCallback(async (item: ClipboardItem) => {
    try {
      await navigator.clipboard.writeText(item.content)
      message.success('已复制到剪贴板')
    } catch {
      message.error('复制失败')
    }
  }, [])

  /** 删除条目 */
  const handleDelete = useCallback(async (id: string) => {
    try {
      await deleteClipboardItem(id)
      setState((s) => ({
        ...s,
        items: s.items.filter((i) => i.id !== id),
        detailItem: s.detailItem?.id === id ? null : s.detailItem
      }))
      message.success('已删除')
    } catch {
      message.error('删除失败')
    }
  }, [])

  /** 固定/取消固定 */
  const handleTogglePin = useCallback(async (id: string) => {
    try {
      const updated = await togglePinClipboardItem(id)
      setState((s) => {
        const items = s.items.map((i) => (i.id === id ? updated : i))
        // 重新排序：固定项在前，其余按时间倒序
        items.sort((a, b) => {
          if (a.isPinned !== b.isPinned) return a.isPinned ? -1 : 1
          return (
            new Date(b.copiedAt).getTime() - new Date(a.copiedAt).getTime()
          )
        })
        return {
          ...s,
          items,
          detailItem: s.detailItem?.id === id ? updated : s.detailItem
        }
      })
      message.success(updated.isPinned ? '已固定' : '已取消固定')
    } catch {
      message.error('操作失败')
    }
  }, [])

  /** 打开详情面板 */
  const openDetail = useCallback((item: ClipboardItem) => {
    setState((s) => ({ ...s, detailItem: item }))
  }, [])

  /** 关闭详情面板 */
  const closeDetail = useCallback(() => {
    setState((s) => ({ ...s, detailItem: null }))
  }, [])

  /** 打开右键菜单 */
  const openContextMenu = useCallback(
    (item: ClipboardItem, position: { x: number; y: number }) => {
      setState((s) => ({
        ...s,
        contextMenuItem: item,
        contextMenuPosition: position
      }))
    },
    []
  )

  /** 关闭右键菜单 */
  const closeContextMenu = useCallback(() => {
    setState((s) => ({
      ...s,
      contextMenuItem: null,
      contextMenuPosition: null
    }))
  }, [])

  /** 加载更多（虚拟滚动到底部时调用） */
  const loadMore = useCallback(() => {
    if (!state.loading && state.hasMore) {
      setState((s) => ({ ...s, page: s.page + 1 }))
      loadItems(false)
    }
  }, [state.loading, state.hasMore, loadItems])

  /** 按内容类型过滤后的列表（搜索过滤已在 API 层完成） */
  const filteredItems = state.items

  /** 根据搜索关键词高亮内容片段 */
  const getHighlightedContent = useCallback(
    (content: string): string => {
      if (!debouncedKeyword) return truncateContent(content)
      const truncated = truncateContent(content)
      const regex = new RegExp(
        `(${debouncedKeyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`,
        'gi'
      )
      return truncated.replace(regex, '<mark>$1</mark>')
    },
    [debouncedKeyword]
  )

  return {
    ...state,
    filteredItems,
    debouncedKeyword,
    setKeyword,
    copyToClipboard,
    handleDelete,
    handleTogglePin,
    openDetail,
    closeDetail,
    openContextMenu,
    closeContextMenu,
    loadMore,
    getHighlightedContent
  }
}

/** 截断内容到 100 字符 */
function truncateContent(content: string, maxLen = 100): string {
  if (content.length <= maxLen) return content
  return content.slice(0, maxLen) + '...'
}

/**
 * 根据内容判断类型图标
 */
export function getContentTypeIcon(
  contentType: ClipboardContentType
): string {
  switch (contentType) {
    case 'code':
      return '💻'
    case 'link':
      return '🔗'
    case 'image':
      return '🖼️'
    default:
      return '📝'
  }
}

/**
 * 获取内容类型标签文本
 */
export function getContentTypeLabel(
  contentType: ClipboardContentType
): string {
  switch (contentType) {
    case 'code':
      return '代码'
    case 'link':
      return '链接'
    case 'image':
      return '图片'
    default:
      return '文本'
  }
}
