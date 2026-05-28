/**
 * 自动滚动 Hook
 * 当用户在底部时自动滚动，用户手动上翻时暂停
 */

import { useCallback, useEffect, useRef, useState } from 'react'

/** 滚动到底部的阈值（像素） */
const SCROLL_THRESHOLD = 100

interface UseAutoScrollOptions {
  /** 是否启用自动滚动 */
  enabled?: boolean
}

interface UseAutoScrollReturn {
  /** 容器 ref */
  containerRef: React.RefObject<HTMLDivElement | null>
  /** 是否在底部 */
  isAtBottom: boolean
  /** 强制滚动到底部 */
  scrollToBottom: () => void
}

export function useAutoScroll(options: UseAutoScrollOptions = {}): UseAutoScrollReturn {
  const { enabled = true } = options
  const containerRef = useRef<HTMLDivElement | null>(null)
  const [isAtBottom, setIsAtBottom] = useState(true)

  const checkIfAtBottom = useCallback(() => {
    const el = containerRef.current
    if (!el) return true

    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight
    return distanceFromBottom < SCROLL_THRESHOLD
  }, [])

  const scrollToBottom = useCallback(() => {
    const el = containerRef.current
    if (!el) return

    el.scrollTo({
      top: el.scrollHeight,
      behavior: 'smooth'
    })
  }, [])

  // 监听滚动事件，判断是否在底部
  useEffect(() => {
    const el = containerRef.current
    if (!el) return

    const handleScroll = (): void => {
      setIsAtBottom(checkIfAtBottom())
    }

    el.addEventListener('scroll', handleScroll, { passive: true })
    return () => el.removeEventListener('scroll', handleScroll)
  }, [checkIfAtBottom])

  // DOM 变化时自动滚动到底部（仅在用户处于底部时）
  useEffect(() => {
    if (!enabled) return

    const el = containerRef.current
    if (!el) return

    const observer = new MutationObserver(() => {
      if (isAtBottom) {
        // 使用 requestAnimationFrame 确保 DOM 更新后再滚动
        requestAnimationFrame(() => {
          el.scrollTop = el.scrollHeight
        })
      }
    })

    observer.observe(el, {
      childList: true,
      subtree: true,
      characterData: true
    })

    return () => observer.disconnect()
  }, [enabled, isAtBottom])

  return {
    containerRef,
    isAtBottom,
    scrollToBottom
  }
}
