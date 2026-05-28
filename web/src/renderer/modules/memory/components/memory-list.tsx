/** 记忆列表组件 */

import { Spin, Pagination } from 'antd'
import { MemoryCard } from './memory-card'
import { EmptyState } from '@/components/empty-state'
import type { MemoryEntry } from '../types/memory'
import styles from './memory-panel.module.css'

interface MemoryListProps {
  /** 记忆列表数据 */
  memories: MemoryEntry[]
  /** 总条数 */
  total: number
  /** 当前页 */
  page: number
  /** 每页条数 */
  pageSize: number
  /** 加载中 */
  loading?: boolean
  /** 翻页回调 */
  onPageChange: (page: number) => void
  /** 点击卡片回调 */
  onCardClick: (memory: MemoryEntry) => void
  /** 是否显示相似度（搜索模式） */
  showSimilarity?: boolean
}

/**
 * 记忆列表
 * 展示长期记忆条目，支持分页和搜索结果模式
 */
export function MemoryList({
  memories,
  total,
  page,
  pageSize,
  loading = false,
  onPageChange,
  onCardClick,
  showSimilarity = false,
}: MemoryListProps) {
  if (loading) {
    return (
      <div className={styles.emptyContainer}>
        <Spin size="large" />
      </div>
    )
  }

  if (memories.length === 0) {
    return (
      <div className={styles.emptyContainer}>
        <EmptyState
          icon="🧠"
          description="AI 会从对话中提炼记忆，自动记录在这里"
        />
      </div>
    )
  }

  return (
    <>
      <div className={styles.listContainer}>
        <div className={styles.memoryGrid}>
          {memories.map((memory) => (
            <MemoryCard
              key={memory.id}
              memory={memory}
              onClick={onCardClick}
              showSimilarity={showSimilarity}
            />
          ))}
        </div>
      </div>

      {!showSimilarity && total > pageSize && (
        <div className={styles.pagination}>
          <Pagination
            current={page}
            pageSize={pageSize}
            total={total}
            onChange={onPageChange}
            showSizeChanger={false}
            showTotal={(t) => `共 ${t} 条记忆`}
            size="small"
          />
        </div>
      )}
    </>
  )
}
