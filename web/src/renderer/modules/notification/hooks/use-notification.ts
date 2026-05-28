/**
 * 通知状态 Hook
 *
 * 整合通知 Store 与 WebSocket 推送，提供通知弹窗功能。
 */

import { useEffect, useCallback } from 'react'
import { notification } from 'antd'
import { useWebSocket } from '@/services/websocket/use-websocket'
import { useNotificationStore } from '@/stores/use-notification-store'
import type { Notification, NotificationType } from '../types/notification'
import { NOTIFICATION_TYPE_ICON } from '../types/notification'
import type { WSMessage } from '@/services/websocket/types'

function generateId(): string {
  return `notif-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`
}

/**
 * 通知状态管理 Hook
 *
 * - 自动订阅 WebSocket notification 消息
 * - 收到推送时弹出 Ant Design Notification
 * - 提供筛选、已读、清除操作
 */
export function useNotification() {
  const { subscribe } = useWebSocket()
  const store = useNotificationStore()

  // 订阅 WebSocket 通知消息
  useEffect(() => {
    const unsub = subscribe('notification', (msg: WSMessage) => {
      const { title, message: body, type, actionUrl } = msg.payload as {
        title?: string
        message?: string
        type?: NotificationType
        actionUrl?: string
      }

      const notif: Notification = {
        id: (msg.event_id as string) || generateId(),
        type: type || 'system_alert',
        title: title || '新通知',
        message: body || '',
        read: false,
        createdAt: new Date(msg.timestamp).toISOString(),
        actionUrl,
      }

      store.addNotification(notif)

      // 弹出 Ant Design 通知弹窗
      const icon = NOTIFICATION_TYPE_ICON[notif.type] || '🔔'
      notification.open({
        message: `${icon} ${notif.title}`,
        description: notif.message,
        duration: 5,
        onClick: notif.actionUrl
          ? () => {
              // 可扩展：导航到对应页面
              console.log('Navigate to:', notif.actionUrl)
            }
          : undefined,
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
        result = result.filter((n) => n.read)
      } else if (readFilter === 'unread') {
        result = result.filter((n) => !n.read)
      }

      return result
    },
    [store.notifications],
  )

  return {
    notifications: store.notifications,
    unreadCount: store.unreadCount,
    markAsRead: store.markAsRead,
    markAllAsRead: store.markAllAsRead,
    clearRead: store.clearRead,
    getFiltered,
  }
}
