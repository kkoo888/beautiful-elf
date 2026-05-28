/** 语义搜索组件 */

import { useCallback, useRef } from 'react'
import { Input, Typography, Button } from 'antd'
import { SearchOutlined, CloseCircleFilled } from '@ant-design/icons'
import styles from './memory-panel.module.css'

const { Text } = Typography

interface MemorySearchProps {
  /** 搜索关键词 */
  value: string
  /** 搜索回调 */
  onSearch: (query: string) => void
  /** 清除搜索回调 */
  onClear: () => void
  /** 是否处于搜索模式 */
  isSearchMode: boolean
  /** 搜索结果数量 */
  resultCount?: number
  /** 是否搜索中 */
  loading?: boolean
}

/**
 * 记忆语义搜索
 * 搜索框突出显示，是核心入口
 */
export function MemorySearch({
  value,
  onSearch,
  onClear,
  isSearchMode,
  resultCount,
  loading = false,
}: MemorySearchProps) {
  const inputRef = useRef<HTMLInputElement>(null)

  const handleSearch = useCallback(
    (val: string) => {
      onSearch(val.trim())
    },
    [onSearch]
  )

  const handleClear = useCallback(() => {
    onClear()
    inputRef.current?.focus()
  }, [onClear])

  return (
    <div className={styles.searchSection}>
      <div className={styles.searchBox}>
        <Input
          ref={inputRef as never}
          placeholder="输入问题，语义检索相关记忆…"
          prefix={<SearchOutlined style={{ color: 'rgba(0,0,0,0.35)', fontSize: 16 }} />}
          suffix={
            isSearchMode ? (
              <CloseCircleFilled
                style={{ color: 'rgba(0,0,0,0.25)', cursor: 'pointer' }}
                onClick={handleClear}
              />
            ) : undefined
          }
          value={value}
          onChange={(e) => {
            if (!e.target.value.trim()) {
              handleClear()
            }
          }}
          onPressEnter={(e) => handleSearch((e.target as HTMLInputElement).value)}
          allowClear={false}
          size="large"
        />
      </div>

      {isSearchMode && (
        <div className={styles.searchInfo}>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {loading
              ? '正在语义检索…'
              : `找到 ${resultCount ?? 0} 条相关记忆`}
          </Text>
          <Button type="link" size="small" onClick={handleClear}>
            清除搜索
          </Button>
        </div>
      )}
    </div>
  )
}
