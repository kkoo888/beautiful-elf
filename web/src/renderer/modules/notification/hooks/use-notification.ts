/**
 * 通知状态 Hook
 *
 * 整合通知 Store 与 WebSocket 推送，提供通知弹窗功能。
 */

import { useEffect, useCallback } from 'react'
import { useWebSocket } from '@/services/websocket/use-websocket'
import { useNotificationStore } from '@/stores/use-notification-store'
import type { NotificationType } from '../types/notification'
import { showNotification } from '../services/notification-toast'
import type { WSMessage } from '@/services/websocket/types'
import type { Notification } from '@/types'

function generateId(): string {
  return `notif-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`
}

/**
 * 通知状态管理 Hook
 *
 * - 自动订阅 WebSocket notification 消息
 * - 收到推送时弹出 Ant Design Notification（带 event_id 去重）
 * - 窗口失焦时额外触发桌面通知
 * - 提供筛选、已读、清除操作
 */
export function useNotification() {
  const { subscribe } = useWebSocket()
  const store = useNotificationStore()

  // 订阅 WebSocket 通知消息
  useEffect(() => {
    const unsub = subscribe('notification', (msg: WSMessage) => {
      const {
        title,
        message: body,
        type,
        actionUrl,
      } = msg.payload as {
        title?: string
        message?: string
        type?: NotificationType
        actionUrl?: string
      }

      const notif: Notification = {
        id: (msg.eventId as string) || generateId(),
        eventId: msg.eventId as string | undefined,
        type: type || 'system_alert',
        title: title || '新通知',
        message: body || '',
        isRead: false,
        createdAt: new Date(msg.timestamp).toISOString(),
        actionUrl,
      }

      store.addNotification(notif)

      // 弹出通知弹窗（内部处理 event_id 去重 + 桌面通知）
      showNotification({
        id: notif.id,
        eventId: notif.eventId,
        type: notif.type,
        title: notif.title,
        body: notif.message,
        isRead: false,
        createdAt: msg.timestamp,
      })
    })

    return unsub
  }, [subscribe, store])

  /** 筛选通知 */
  const getFiltered = useCallback(
    (type?: NotificationType | 'all', readFilter?: 'all' | 'read' | 'unread') => {
      let result = store.notifications

      if (type && type !== 'all') {
        result = result.filter((n) => n.type === type)
      }

      if (readFilter === 'read') {
        result = result.filter((n) => n.isRead)
      } else if (readFilter === 'unread') {
        result = result.filter((n) => !n.isRead)
      }

      return result
    },
    [store.notifications]
  )

  /** 按类型筛选通知 */
  const filterByType = useCallback(
    (type: NotificationType | 'all') => {
      return getFiltered(type)
    },
    [getFiltered]
  )

  return {
    notifications: store.notifications,
    unreadCount: store.unreadCount,
    markAsRead: store.markAsRead,
    markAllAsRead: store.markAllAsRead,
    clearRead: store.clearRead,
    getFiltered,
    filterByType,
  }
}
