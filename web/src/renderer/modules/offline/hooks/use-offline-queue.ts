/** 离线消息队列 Hook */

import { useState, useCallback, useRef } from 'react'
import { generateId } from '@/utils'
import { apiClient } from '@/services/api-client'
import type { OfflineMessage, OfflineStorageStats } from '../types/offline'
import {
  saveMessage,
  getPendingMessages,
  removeMessage,
  markMessageStatus,
  getStorageStats,
} from '../services/offline-storage'

/** 最大重试次数 */
const MAX_RETRY = 3

interface UseOfflineQueueReturn {
  queueLength: number
  isFlushing: boolean
  stats: OfflineStorageStats
  enqueueMessage: (conversationId: string, content: string) => Promise<void>
  flushQueue: () => Promise<number>
  getQueue: () => Promise<OfflineMessage[]>
  refreshStats: () => Promise<void>
}

export function useOfflineQueue(): UseOfflineQueueReturn {
  const [queueLength, setQueueLength] = useState(0)
  const [isFlushing, setIsFlushing] = useState(false)
  const [stats, setStats] = useState<OfflineStorageStats>({ count: 0, sizeBytes: 0 })
  const sendingRef = useRef(false)

  /** 刷新统计 */
  const refreshStats = useCallback(async () => {
    try {
      const s = await getStorageStats()
      setStats(s)
      setQueueLength(s.count)
    } catch {
      // 忽略
    }
  }, [])

  /** 入队离线消息 */
  const enqueueMessage = useCallback(
    async (conversationId: string, content: string) => {
      const msg: OfflineMessage = {
        id: generateId(),
        conversationId,
        content,
        createdAt: Date.now(),
        status: 'pending',
        retryCount: 0,
      }
      await saveMessage(msg)
      await refreshStats()
    },
    [refreshStats]
  )

  /** 刷新队列（按 createdAt 升序逐条发送） */
  const flushQueue = useCallback(async (): Promise<number> => {
    if (sendingRef.current) return 0
    sendingRef.current = true
    setIsFlushing(true)

    try {
      const pending = await getPendingMessages()
      let sentCount = 0

      for (const msg of retryable(pending, MAX_RETRY)) {
        try {
          // 标记为发送中
          await markMessageStatus(msg.id, 'sending')

          // 调用后端消息接口发送
          await apiClient.post('/messages', {
            conversationId: Number(msg.conversationId),
            role: 'user',
            content: msg.content,
          })

          await removeMessage(msg.id)
          sentCount++
        } catch {
          // 发送失败
          if (msg.retryCount >= MAX_RETRY) {
            // 超过重试上限，标记为 failed
            await markMessageStatus(msg.id, 'failed')
          } else {
            // 回退为 pending 等待下次重试
            await markMessageStatus(msg.id, 'pending')
          }
        }
      }

      await refreshStats()
      return sentCount
    } finally {
      sendingRef.current = false
      setIsFlushing(false)
    }
  }, [refreshStats])

  /** 获取当前队列 */
  const getQueue = useCallback(async () => {
    return getPendingMessages()
  }, [])

  return { queueLength, isFlushing, stats, enqueueMessage, flushQueue, getQueue, refreshStats }
}

/**
 * 生成可重试的消息迭代器
 * 跳过已超过最大重试次数的消息（标记为 failed）
 */
function* retryable(messages: OfflineMessage[], maxRetry: number): Generator<OfflineMessage> {
  for (const msg of messages) {
    if (msg.retryCount < maxRetry) {
      yield msg
    }
  }
}
