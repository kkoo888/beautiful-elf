/** 记忆模块主面板 */

import { useState, useCallback } from 'react'
import { App } from 'antd'
import { PageHeader } from '@/components/page-header'
import { MemorySearch } from './memory-search'
import { MemoryList } from './memory-list'
import { MemoryDetail } from './memory-detail'
import { useMemory } from '../hooks/use-memory'
import type { MemoryEntry } from '../types/memory'
import styles from './memory-panel.module.css'

/**
 * 记忆面板
 * 核心入口：语义搜索 + 记忆列表 + 详情 Drawer
 */
export default function MemoryPanel() {
  const { message } = App.useApp()
  const {
    memories,
    total,
    page,
    pageSize,
    isLoading,
    setPage,
    searchQuery,
    setSearchQuery,
    searchResults,
    isSearching,
    isSearchMode,
    doSearch,
    clearSearch,
    deleteMemoryMut,
  } = useMemory()

  // 详情 Drawer 状态
  const [detailOpen, setDetailOpen] = useState(false)
  const [selectedMemory, setSelectedMemory] = useState<MemoryEntry | null>(null)

  const handleCardClick = useCallback((memory: MemoryEntry) => {
    setSelectedMemory(memory)
    setDetailOpen(true)
  }, [])

  const handleDetailClose = useCallback(() => {
    setDetailOpen(false)
  }, [])

  const handleDelete = useCallback(
    async (id: string) => {
      try {
        await deleteMemoryMut(id)
        message.success('记忆已删除')
      } catch {
        message.error('删除失败，请重试')
      }
    },
    [deleteMemoryMut]
  )

  // 当前展示的数据
  const displayMemories = isSearchMode ? searchResults : memories

  return (
    <div className={styles.panel}>
      <PageHeader title="🧠 记忆" description="长期记忆与语义检索" />

      <MemorySearch
        value={searchQuery}
        onSearch={doSearch}
        onClear={clearSearch}
        isSearchMode={isSearchMode}
        resultCount={searchResults.length}
        loading={isSearching}
      />

      <MemoryList
        memories={displayMemories}
        total={isSearchMode ? searchResults.length : total}
        page={page}
        pageSize={pageSize}
        loading={isLoading || isSearching}
        onPageChange={setPage}
        onCardClick={handleCardClick}
        showSimilarity={isSearchMode}
      />

      <MemoryDetail
        memory={selectedMemory}
        open={detailOpen}
        onClose={handleDetailClose}
        onDelete={handleDelete}
      />
    </div>
  )
}
