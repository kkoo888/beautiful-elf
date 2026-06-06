/**
 * 通知弹窗服务
 *
 * 封装 Ant Design Notification 弹窗 + Electron 桌面通知，
 * 支持 event_id LRU 去重（100 条）。
 */

import { notification } from 'antd'
import type { NotificationMessage } from '../types/notification'

/** event_id LRU 去重缓存 (100 条) */
const eventIdCache = new Map<string, number>()
const MAX_CACHE_SIZE = 100

/**
 * 显示通知弹窗
 *
 * - 基于 event_id 去重，避免重复弹窗
 * - 使用 Ant Design Notification 弹窗
 * - 窗口失焦时额外触发 Electron 桌面通知
 */
export function showNotification(data: NotificationMessage): void {
  // 去重检查
  if (data.eventId && eventIdCache.has(data.eventId)) return

  // LRU 缓存管理
  if (eventIdCache.size >= MAX_CACHE_SIZE) {
    const firstKey = eventIdCache.keys().next().value
    if (firstKey !== undefined) {
      eventIdCache.delete(firstKey)
    }
  }
  if (data.eventId) {
    eventIdCache.set(data.eventId, Date.now())
  }

  // Ant Design Notification 弹窗
  notification.open({
    message: data.title,
    description: data.body,
    placement: 'topRight',
    duration: 5,
    onClick: () => {
      // 点击跳转到通知面板
      window.location.hash = '#/notification'
    },
  })

  // Electron 桌面通知 (如果窗口不在前台)
  if (typeof document !== 'undefined' && document.hidden) {
    try {
      new window.Notification(data.title, { body: data.body })
    } catch {
      // Notification API 不可用时静默忽略
    }
  }
}
