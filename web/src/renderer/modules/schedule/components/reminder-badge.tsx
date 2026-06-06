/** 提醒标记组件 */

import { memo } from 'react'
import { ClockCircleOutlined } from '@ant-design/icons'
import styles from './schedule-panel.module.css'

interface ReminderBadgeProps {
  /** 提前分钟数 */
  minutes: number
}

const formatReminder = (minutes: number): string => {
  if (minutes <= 0) return ''
  if (minutes < 60) return `${minutes}分钟`
  if (minutes < 1440) return `${Math.floor(minutes / 60)}小时`
  return `${Math.floor(minutes / 1440)}天`
}

export const ReminderBadge = memo<ReminderBadgeProps>(function ReminderBadge({ minutes }) {
  const text = formatReminder(minutes)
  if (!text) return null

  return (
    <span className={styles.reminderBadge}>
      <ClockCircleOutlined />
      提前{text}
    </span>
  )
})
