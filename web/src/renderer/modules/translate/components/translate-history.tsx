/**
 * 翻译历史组件
 * 显示历史翻译记录列表，支持点击回填和收藏
 */

import React, { useEffect } from 'react'
import { Button, Tooltip, Spin, Empty } from 'antd'
import { HistoryOutlined, StarOutlined, StarFilled } from '@ant-design/icons'
import styles from './translate-panel.module.css'
import type { TranslateResult, Language } from '../types/translate'

interface TranslateHistoryProps {
  /** 翻译历史列表 */
  history: TranslateResult[]
  /** 是否正在加载 */
  isLoading: boolean
  /** 支持的语言列表 */
  languages: Language[]
  /** 加载历史 */
  onLoad: () => void
  /** 点击历史项回填 */
  onSelect: (item: TranslateResult) => void
  /** 收藏/取消收藏 */
  onFavorite: (id: string, favorite: boolean) => void
}

/**
 * 格式化相对时间
 */
function formatRelativeTime(dateStr: string): string {
  const now = Date.now()
  const date = new Date(dateStr).getTime()
  const diff = now - date

  if (diff < 60_000) return '刚刚'
  if (diff < 3600_000) return `${Math.floor(diff / 60_000)} 分钟前`
  if (diff < 86400_000) return `${Math.floor(diff / 3600_000)} 小时前`
  if (diff < 604800_000) return `${Math.floor(diff / 86400_000)} 天前`
  return new Date(dateStr).toLocaleDateString('zh-CN')
}

/**
 * 获取语言名称
 */
function getLangName(languages: Language[], code: string): string {
  return languages.find((l) => l.code === code)?.name ?? code
}

/**
 * 翻译历史侧边栏
 */
export const TranslateHistory: React.FC<TranslateHistoryProps> = ({
  history,
  isLoading,
  languages,
  onLoad,
  onSelect,
  onFavorite
}) => {
  useEffect(() => {
    onLoad()
  }, [onLoad])

  return (
    <div className={styles.historyPanel}>
      <div className={styles.historyHeader}>
        <h4 className={styles.historyTitle}>
          <HistoryOutlined style={{ marginRight: 6 }} />
          翻译历史
        </h4>
        <Tooltip title="刷新">
          <Button
            type="text"
            size="small"
            icon={<HistoryOutlined />}
            onClick={onLoad}
            loading={isLoading}
          />
        </Tooltip>
      </div>

      <div className={styles.historyList}>
        {isLoading ? (
          <div
            style={{
              display: 'flex',
              justifyContent: 'center',
              padding: 32
            }}
          >
            <Spin size="small" />
          </div>
        ) : history.length === 0 ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description="暂无翻译历史"
            style={{ padding: '32px 0' }}
          />
        ) : (
          history.map((item) => (
            <div
              key={item.id}
              className={styles.historyItem}
              onClick={() => onSelect(item)}
            >
              <span className={styles.historySource}>{item.sourceText}</span>
              <span className={styles.historyTarget}>{item.targetText}</span>
              <div className={styles.historyMeta}>
                <span className={styles.historyLang}>
                  {getLangName(languages, item.sourceLang)} →{' '}
                  {getLangName(languages, item.targetLang)} ·{' '}
                  {formatRelativeTime(item.createdAt)}
                </span>
                <span
                  className={`${styles.historyMode} ${
                    item.mode === 'terminology' ? styles.historyModeTerminology : ''
                  }`}
                >
                  {item.mode === 'terminology' ? '📚 术语' : '🌐 通用'}
                </span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
