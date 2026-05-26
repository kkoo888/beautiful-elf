import { useEffect, useRef, useCallback, useState } from 'react'

/**
 * 自动滚动到底部
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
