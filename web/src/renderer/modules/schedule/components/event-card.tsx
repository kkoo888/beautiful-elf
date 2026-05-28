/** 日程事件卡片（在日历格子中显示） */

import { memo } from 'react'
import dayjs from 'dayjs'
import type { Schedule } from '@/types'
import styles from './schedule-panel.module.css'

interface EventCardProps {
  event: Schedule
  /** 是否显示时间（月视图中不显示） */
  showTime?: boolean
  /** 点击事件 */
  onClick?: (event: Schedule) => void
}

export const EventCard = memo<EventCardProps>(function EventCard({
  event,
  showTime = false,
  onClick,
}) {
  const bgColor = event.color || '#f97316'

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    onClick?.(event)
  }

  return (
    <div
      className={styles.eventCard}
      style={{ backgroundColor: bgColor }}
      onClick={handleClick}
      title={event.title}
    >
      <span className={styles.eventTitle}>{event.title}</span>
      {showTime && !event.is_all_day && (
        <span className={styles.eventTime}>{dayjs(event.start_time).format('HH:mm')}</span>
      )}
    </div>
  )
})
