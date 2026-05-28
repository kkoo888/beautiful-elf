import { useEffect, useRef, useCallback } from 'react'

/**
 * 聊天窗口自动滚动 Hook
 * 新消息到来时自动滚到底部，用户手动滚动时暂停
 */
export function useAutoScroll(dependency: unknown) {
  const containerRef = useRef<HTMLDivElement>(null)
  const shouldAutoScroll = useRef(true)

  const scrollToBottom = useCallback(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight
    }
  }, [])

  const handleScroll = useCallback(() => {
    if (containerRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = containerRef.current
      // 距离底部 50px 以内视为"在底部"
      shouldAutoScroll.current = scrollHeight - scrollTop - clientHeight < 50
    }
  }, [])

  useEffect(() => {
    if (shouldAutoScroll.current) {
      scrollToBottom()
    }
  }, [dependency, scrollToBottom])

  return { containerRef, handleScroll, scrollToBottom }
}
