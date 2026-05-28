/**
 * 通知主面板
 *
 * 展示通知列表，支持类型筛选、标记已读、清除已读。
 */

import { useState } from 'react'
import { Segmented, Button, Empty, Badge } from 'antd'
import { CheckOutlined, DeleteOutlined } from '@ant-design/icons'
import { useNotification } from '../hooks/use-notification'
import { NotificationItem } from './notification-item'
import type { NotificationType } from '../types/notification'
import { NOTIFICATION_TYPE_LABEL } from '../types/notification'
import styles from './notification-panel.module.css'

type FilterValue = 'all' | NotificationType

const FILTER_OPTIONS = [
  { label: '全部', value: 'all' },
  ...Object.entries(NOTIFICATION_TYPE_LABEL).map(([value, label]) => ({
    label,
    value,
  })),
]

export function NotificationPanel() {
  const [filter, setFilter] = useState<FilterValue>('all')
  const { notifications, unreadCount, markAsRead, markAllAsRead, clearRead, getFiltered } =
    useNotification()

  const filtered = getFiltered(filter === 'all' ? undefined : filter)

  return (
    <div className={styles.panel}>
      {/* 头部 */}
      <div className={styles.header}>
        <div className={styles.headerTitle}>
          <span>🔔 通知中心</span>
          {unreadCount > 0 && (
            <Badge count={unreadCount} size="small" className={styles.headerBadge} />
          )}
        </div>
        <div className={styles.headerActions}>
          <Button
            type="text"
            size="small"
            icon={<CheckOutlined />}
            onClick={markAllAsRead}
            disabled={unreadCount === 0}
          >
            全部已读
          </Button>
          <Button
            type="text"
            size="small"
            icon={<DeleteOutlined />}
            onClick={clearRead}
            disabled={notifications.every((n) => !n.read)}
          >
            清除已读
          </Button>
        </div>
      </div>

      {/* 筛选 */}
      <div className={styles.filterBar}>
        <Segmented
          options={FILTER_OPTIONS}
          value={filter}
          onChange={(val) => setFilter(val as FilterValue)}
          size="small"
          block
        />
      </div>

      {/* 通知列表 */}
      <div className={styles.list}>
        {filtered.length === 0 ? (
          <Empty
            description="暂无通知"
            className={styles.empty}
          />
        ) : (
          filtered.map((n) => (
            <NotificationItem key={n.id} notification={n} onRead={markAsRead} />
          ))
        )}
      </div>
    </div>
  )
}
