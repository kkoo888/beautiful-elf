/** 记忆模块主面板 — 三 Tab 布局 */

import { useState, useCallback } from 'react'
import { App, Tabs } from 'antd'
import {
  SearchOutlined, CalendarOutlined, BookOutlined,
  PlusOutlined, BarChartOutlined, ClockCircleOutlined,
  SettingOutlined,
} from '@ant-design/icons'
import { PageHeader } from '@/components/page-header'
import { MemorySearch } from './memory-search'
import { MemoryList } from './memory-list'
import { MemoryDetail } from './memory-detail'
import { DailyLogTab } from './daily-log-tab'
import { LongTermTab } from './longterm-tab'
import { EpisodeTab } from './episode-tab'
import { OptimizationTab } from './optimization-tab'
import { SchedulerTab } from './scheduler-tab'
import { MemorySettingsTab } from './memory-settings-tab'
import { useMemory } from '../hooks/use-memory'
import type { MemoryEntry } from '../types/memory'
import styles from './memory-panel.module.css'

/**
 * 记忆面板 — 三 Tab 布局
 * - 向量记忆：语义搜索 + 列表
 * - 每日日志：Markdown 日记
 * - 长期记忆：MEMORY 编辑
 */
export default function MemoryPanel() {
  const { message } = App.useApp()
  const [activeTab, setActiveTab] = useState('vector')
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

  const tabItems = [
    {
      key: 'vector',
      label: (
        <span>
          <SearchOutlined />
          向量记忆
        </span>
      ),
      children: (
        <div className={styles.vectorTabContent}>
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
        </div>
      ),
    },
    {
      key: 'episode',
      label: (
        <span>
          <PlusOutlined />
          经历
        </span>
      ),
      children: <EpisodeTab />,
    },
    {
      key: 'optimization',
      label: (
        <span>
          <BarChartOutlined />
          优化
        </span>
      ),
      children: <OptimizationTab />,
    },
    {
      key: 'daily',
      label: (
        <span>
          <CalendarOutlined />
          每日日志
        </span>
      ),
      children: <DailyLogTab />,
    },
    {
      key: 'longterm',
      label: (
        <span>
          <BookOutlined />
          长期记忆
        </span>
      ),
      children: <LongTermTab />,
    },
    {
      key: 'scheduler',
      label: (
        <span>
          <ClockCircleOutlined />
          定时任务
        </span>
      ),
      children: <SchedulerTab />,
    },
    {
      key: 'settings',
      label: (
        <span>
          <SettingOutlined />
          设置
        </span>
      ),
      children: <MemorySettingsTab />,
    },
  ]

  return (
    <div className={styles.panel}>
      <div className={styles.panelHeader}>
        <PageHeader title="🧠 记忆" description="向量检索 · 每日日志 · 长期记忆" />
      </div>

      <div className={styles.tabWrapper}>
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={tabItems}
          style={{ padding: '0 16px' }}
        />
      </div>

      <MemoryDetail
        memory={selectedMemory}
        open={detailOpen}
        onClose={handleDetailClose}
        onDelete={handleDelete}
      />
    </div>
  )
}
