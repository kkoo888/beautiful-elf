/** 记忆模块状态 hooks（TanStack Query） */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState, useCallback } from 'react'
import type { MemoryEntry, MemoryListResponse, MemorySearchResult } from '../types/memory'
import { fetchMemories, searchMemories, deleteMemory } from '../services/memory-api'

const QUERY_KEY = ['memories']

export interface UseMemoryReturn {
  /** 记忆列表 */
  memories: MemoryEntry[]
  /** 总条数 */
  total: number
  /** 当前页 */
  page: number
  /** 每页条数 */
  pageSize: number
  /** 加载中 */
  isLoading: boolean
  /** 错误 */
  error: Error | null
  /** 翻页 */
  setPage: (page: number) => void
  /** 搜索关键词 */
  searchQuery: string
  setSearchQuery: (q: string) => void
  /** 搜索结果 */
  searchResults: MemoryEntry[]
  /** 搜索中 */
  isSearching: boolean
  /** 是否处于搜索模式 */
  isSearchMode: boolean
  /** 执行搜索 */
  doSearch: (query: string) => void
  /** 清除搜索 */
  clearSearch: () => void
  /** 删除记忆 */
  deleteMemoryMut: (id: string) => Promise<void>
  /** 是否有正在提交的操作 */
  isMutating: boolean
}

export function useMemory(): UseMemoryReturn {
  const queryClient = useQueryClient()
  const [page, setPage] = useState(1)
  const [searchQuery, setSearchQuery] = useState('')
  const [isSearchMode, setIsSearchMode] = useState(false)

  // 记忆列表查询
  const {
    data: listData,
    isLoading,
    error,
  } = useQuery<MemoryListResponse>({
    queryKey: [...QUERY_KEY, 'list', page],
    queryFn: () => fetchMemories({ page, pageSize: 20 }),
    enabled: !isSearchMode,
  })

  // 语义搜索查询
  const {
    data: searchData,
    isLoading: isSearching,
    refetch: refetchSearch,
  } = useQuery<MemorySearchResult>({
    queryKey: [...QUERY_KEY, 'search', searchQuery],
    queryFn: () => searchMemories(searchQuery),
    enabled: false, // 手动触发
  })

  // 删除记忆
  const deleteMut = useMutation({
    mutationFn: (id: string) => deleteMemory(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEY })
    },
  })

  const doSearch = useCallback(
    (query: string) => {
      setSearchQuery(query)
      if (query.trim()) {
        setIsSearchMode(true)
        // 延迟一帧确保 queryKey 更新后再触发
        setTimeout(() => refetchSearch(), 0)
      } else {
        setIsSearchMode(false)
      }
    },
    [refetchSearch]
  )

  const clearSearch = useCallback(() => {
    setSearchQuery('')
    setIsSearchMode(false)
  }, [])

  return {
    memories: listData?.items ?? [],
    total: listData?.total ?? 0,
    page,
    pageSize: listData?.pageSize ?? 20,
    isLoading,
    error: error as Error | null,
    setPage,
    searchQuery,
    setSearchQuery,
    searchResults: searchData?.items ?? [],
    isSearching,
    isSearchMode,
    doSearch,
    clearSearch,
    deleteMemoryMut: deleteMut.mutateAsync,
    isMutating: deleteMut.isPending,
  }
}
