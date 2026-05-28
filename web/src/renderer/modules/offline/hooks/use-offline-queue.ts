/** 离线消息队列 Hook */

import { useState, useCallback, useRef } from 'react'
import { generateId } from '@/utils'
import type { OfflineMessage } from '../types/offline'
import { saveMessage, getPendingMessages, deleteMessage } from '../services/offline-storage'

interface UseOfflineQueueReturn {
  queueLength: number
  isFlushing: boolean
  enqueueMessage: (conversationId: string, content: string) => Promise<void>
  flushQueue: () => Promise<number>
  getQueue: () => Promise<OfflineMessage[]>
}

export function useOfflineQueue(): UseOfflineQueueReturn {
  const [queueLength, setQueueLength] = useState(0)
  const [isFlushing, setIsFlushing] = useState(false)
  const sendingRef = useRef(false)

  /** 入队离线消息 */
  const enqueueMessage = useCallback(async (conversationId: string, content: string) => {
    const msg: OfflineMessage = {
      id: generateId(),
      conversationId,
      content,
      createdAt: Date.now(),
      status: 'pending',
      retryCount: 0,
    }
    await saveMessage(msg)
    setQueueLength((prev) => prev + 1)
  }, [])

  /** 刷新队列（发送所有待发送消息） */
  const flushQueue = useCallback(async (): Promise<number> => {
    if (sendingRef.current) return 0
    sendingRef.current = true
    setIsFlushing(true)

    try {
      const pending = await getPendingMessages()
      let sentCount = 0

      for (const msg of pending) {
        try {
          // TODO: 接入真实 API 发送
          // await apiClient.post('/messages', { conversationId: msg.conversationId, content: msg.content })
          await deleteMessage(msg.id)
          sentCount++
        } catch {
          // 发送失败，保留在队列中
        }
      }

      setQueueLength((prev) => Math.max(0, prev - sentCount))
      return sentCount
    } finally {
      sendingRef.current = false
      setIsFlushing(false)
    }
  }, [])

  /** 获取当前队列 */
  const getQueue = useCallback(async () => {
    return getPendingMessages()
  }, [])

  return { queueLength, isFlushing, enqueueMessage, flushQueue, getQueue }
}
