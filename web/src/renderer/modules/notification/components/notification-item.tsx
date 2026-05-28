/**
 * 单条通知组件
 */

import { Tag } from 'antd'
import type { Notification } from '../types/notification'
import { NOTIFICATION_TYPE_ICON, NOTIFICATION_TYPE_LABEL } from '../types/notification'
import styles from './notification-panel.module.css'

interface NotificationItemProps {
  notification: Notification
  onRead: (id: string) => void
}

export function NotificationItem({ notification, onRead }: NotificationItemProps) {
  const icon = NOTIFICATION_TYPE_ICON[notification.type] || '🔔'
  const label = NOTIFICATION_TYPE_LABEL[notification.type] || '通知'

  const timeStr = formatTime(notification.createdAt)

  return (
    <div
      className={`${styles.item} ${notification.read ? styles.itemRead : styles.itemUnread}`}
      onClick={() => {
        if (!notification.read) onRead(notification.id)
      }}
    >
      <div className={styles.itemHeader}>
        <span className={styles.itemIcon}>{icon}</span>
        <span className={styles.itemTitle}>{notification.title}</span>
        <Tag className={styles.itemTag}>{label}</Tag>
      </div>
      <div className={styles.itemMessage}>{notification.message}</div>
      <div className={styles.itemFooter}>
        <span className={styles.itemTime}>{timeStr}</span>
        {!notification.read && <span className={styles.itemDot} />}
      </div>
    </div>
  )
}

function formatTime(isoString: string): string {
  const date = new Date(isoString)
  const now = new Date()
  const diff = now.getTime() - date.getTime()

  // 1 分钟内
  if (diff < 60_000) return '刚刚'
  // 1 小时内
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)} 分钟前`
  // 今天内
  if (
    date.getFullYear() === now.getFullYear() &&
    date.getMonth() === now.getMonth() &&
    date.getDate() === now.getDate()
  ) {
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  }
  // 更早
  return date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
}
