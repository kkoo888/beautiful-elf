/** 单条记忆卡片组件 */

import { useCallback } from 'react'
import { Card, Tag, Typography, Tooltip } from 'antd'
import { MessageOutlined, ClockCircleOutlined } from '@ant-design/icons'
import { formatRelativeTime } from '@/utils'
import type { MemoryEntry } from '../types/memory'
import styles from './memory-panel.module.css'

const { Text, Paragraph } = Typography

/** 标签颜色映射 */
const TAG_COLORS: string[] = [
  'blue',
  'green',
  'orange',
  'purple',
  'cyan',
  'magenta',
  'geekblue',
  'gold',
]

function getTagColor(tag: string): string {
  let hash = 0
  for (let i = 0; i < tag.length; i++) {
    hash = (hash << 5) - hash + tag.charCodeAt(i)
  }
  return TAG_COLORS[Math.abs(hash) % TAG_COLORS.length]
}

interface MemoryCardProps {
  /** 记忆数据 */
  memory: MemoryEntry
  /** 点击卡片回调 */
  onClick: (memory: MemoryEntry) => void
  /** 是否显示相似度（搜索模式） */
  showSimilarity?: boolean
}

/**
 * 记忆卡片
 * 显示摘要、来源会话、时间、标签，搜索模式下显示相似度
 */
export function MemoryCard({ memory, onClick, showSimilarity = false }: MemoryCardProps) {
  const handleClick = useCallback(() => {
    onClick(memory)
  }, [memory, onClick])

  const similarityPercent = memory.similarity
    ? `${Math.round(memory.similarity * 100)}%`
    : undefined

  return (
    <Card
      className={styles.card}
      hoverable
      onClick={handleClick}
      styles={{ body: { padding: '12px 16px' } }}
    >
      <div className={styles.cardBody}>
        {/* 摘要 */}
        <Paragraph className={styles.summary} style={{ marginBottom: 0 }}>
          {memory.summary}
        </Paragraph>

        {/* 标签 */}
        {memory.tags.length > 0 && (
          <div className={styles.tagList}>
            {memory.tags.map((tag) => (
              <Tag key={tag} color={getTagColor(tag)} className={styles.tag}>
                {tag}
              </Tag>
            ))}
          </div>
        )}

        {/* 元信息 */}
        <div className={styles.cardMeta}>
          <div className={styles.metaLeft}>
            <Tooltip title={`来源会话: ${memory.conversationId}`}>
              <span>
                <MessageOutlined style={{ marginRight: 4 }} />
                {memory.conversationId}
              </span>
            </Tooltip>
            <span>
              <ClockCircleOutlined style={{ marginRight: 4 }} />
              {formatRelativeTime(memory.createdAt)}
            </span>
          </div>

          <div className={styles.metaRight}>
            {showSimilarity && similarityPercent && (
              <Tag className={styles.similarityBadge} color="geekblue">
                相似度 {similarityPercent}
              </Tag>
            )}
          </div>
        </div>
      </div>
    </Card>
  )
}
