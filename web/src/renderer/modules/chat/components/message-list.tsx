/**
 * 消息列表组件
 * 使用 react-window 虚拟滚动，支持 1000+ 消息不卡顿
 */

import React, { useCallback, useEffect, useMemo, useRef } from 'react'
import { FixedSizeList as VirtualList } from 'react-window'
import styles from './chat-panel.module.css'
import { MessageBubble } from './message-bubble'
import { ThinkingIndicator } from './thinking-indicator'
import type { ChatMessage, FeedbackData } from '../types/chat'

/** 消息行高（需要与实际渲染高度一致） */
const MESSAGE_ROW_HEIGHT = 120

/** 预估高度（用于动态计算） */
const ESTIMATED_ITEM_SIZE = 120

interface MessageListProps {
  /** 消息列表 */
  messages: ChatMessage[]
  /** 是否正在加载 */
  isLoading: boolean
  /** 提交反馈回调 */
  onFeedback?: (data: FeedbackData) => Promise<void>
}

/** 虚拟列表行组件 */
interface RowProps {
  index: number
  style: React.CSSProperties
  data: {
    messages: ChatMessage[]
    isLoading: boolean
    onFeedback?: (data: FeedbackData) => Promise<void>
  }
}

const Row: React.FC<RowProps> = React.memo(({ index, style, data }) => {
  const { messages, isLoading, onFeedback } = data
  const message = messages[index]

  if (!message) return null

  return (
    <div style={style}>
      <MessageBubble message={message} onFeedback={onFeedback} />
    </div>
  )
})

Row.displayName = 'MessageRow'

export const MessageList: React.FC<MessageListProps> = ({ messages, isLoading, onFeedback }) => {
  const listRef = useRef<VirtualList>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  // 传递给虚拟行的数据
  const itemData = useMemo(
    () => ({ messages, isLoading, onFeedback }),
    [messages, isLoading, onFeedback]
  )

  // 新消息到来时滚动到底部
  useEffect(() => {
    if (listRef.current && messages.length > 0) {
      listRef.current.scrollToItem(messages.length - 1, 'end')
    }
  }, [messages.length])

  // 内容更新时也滚动（流式更新）
  useEffect(() => {
    if (listRef.current && messages.length > 0) {
      // 使用 requestAnimationFrame 确保 DOM 已更新
      requestAnimationFrame(() => {
        listRef.current?.scrollToItem(messages.length - 1, 'end')
      })
    }
  }, [messages])

  // 空状态
  if (messages.length === 0) {
    return (
      <div className={styles.emptyState}>
        <div className={styles.emptyIcon}>💬</div>
        <div className={styles.emptyText}>开始对话吧</div>
        <div className={styles.emptySubtext}>输入你的问题，AI 助手会为你解答</div>
      </div>
    )
  }

  return (
    <div className={styles.virtualListContainer} ref={containerRef}>
      <VirtualList
        ref={listRef}
        height={600} // 容器高度，实际由 CSS flex 控制
        width="100%"
        itemCount={messages.length}
        itemSize={ESTIMATED_ITEM_SIZE}
        itemData={itemData}
        overscanCount={5}
        style={{ overflowX: 'hidden' }}
      >
        {Row}
      </VirtualList>
      {isLoading && <ThinkingIndicator visible />}
    </div>
  )
}

/**
 * 简化版消息列表（不使用虚拟滚动，用于消息较少的场景）
 * 使用 MutationObserver 实现自动滚动
 */
export const SimpleMessageList: React.FC<MessageListProps> = ({
  messages,
  isLoading,
  onFeedback,
}) => {
  const containerRef = useRef<HTMLDivElement>(null)
  const isAtBottomRef = useRef(true)

  // 检查是否在底部
  const checkAtBottom = useCallback(() => {
    const el = containerRef.current
    if (!el) return true
    return el.scrollHeight - el.scrollTop - el.clientHeight < 100
  }, [])

  // 滚动到底部
  const scrollToBottom = useCallback(() => {
    const el = containerRef.current
    if (!el) return
    el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
  }, [])

  // 监听滚动
  useEffect(() => {
    const el = containerRef.current
    if (!el) return

    const handleScroll = (): void => {
      isAtBottomRef.current = checkAtBottom()
    }
    el.addEventListener('scroll', handleScroll, { passive: true })
    return () => el.removeEventListener('scroll', handleScroll)
  }, [checkAtBottom])

  // 新消息自动滚动
  useEffect(() => {
    if (isAtBottomRef.current) {
      requestAnimationFrame(scrollToBottom)
    }
  }, [messages, scrollToBottom])

  if (messages.length === 0) {
    return (
      <div className={styles.emptyState}>
        <div className={styles.emptyIcon}>💬</div>
        <div className={styles.emptyText}>开始对话吧</div>
        <div className={styles.emptySubtext}>输入你的问题，AI 助手会为你解答</div>
      </div>
    )
  }

  return (
    <div className={styles.messageList} ref={containerRef}>
      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} onFeedback={onFeedback} />
      ))}
      {isLoading && <ThinkingIndicator visible />}
    </div>
  )
}
