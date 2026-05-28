/** 日历视图组件（月/周/日切换） */

import { memo, useMemo, useCallback } from 'react'
import { Button, Segmented, Tooltip } from 'antd'
import { LeftOutlined, RightOutlined, CalendarOutlined } from '@ant-design/icons'
import dayjs, { type Dayjs } from 'dayjs'
import type { Schedule } from '@/types'
import type { CalendarViewMode } from '../types/schedule'
import { EventCard } from './event-card'
import styles from './schedule-panel.module.css'

const WEEKDAYS = ['日', '一', '二', '三', '四', '五', '六']
const HOURS = Array.from({ length: 24 }, (_, i) => i)
const MAX_EVENTS_DISPLAY = 3

interface CalendarViewProps {
  viewMode: CalendarViewMode
  selectedDate: Dayjs
  today: Dayjs
  schedules: Schedule[]
  schedulesByDate: Map<string, Schedule[]>
  onDateSelect: (date: Dayjs) => void
  onViewModeChange: (mode: CalendarViewMode) => void
  onPrev: () => void
  onNext: () => void
  onToday: () => void
  onEventClick: (event: Schedule) => void
  onDateClick: (date: Dayjs) => void
}

export const CalendarView = memo<CalendarViewProps>(function CalendarView({
  viewMode,
  selectedDate,
  today,
  schedulesByDate,
  onDateSelect,
  onViewModeChange,
  onPrev,
  onNext,
  onToday,
  onEventClick,
  onDateClick,
}) {
  // ─── 月视图 ──────────────────────────────────────

  const monthDays = useMemo(() => {
    const start = selectedDate.startOf('month').startOf('week')
    const end = selectedDate.endOf('month').endOf('week')
    const days: Dayjs[] = []
    let cursor = start
    while (cursor.isBefore(end) || cursor.isSame(end, 'day')) {
      days.push(cursor)
      cursor = cursor.add(1, 'day')
    }
    return days
  }, [selectedDate])

  const renderMonthView = () => (
    <div>
      <div className={styles.monthGrid}>
        {WEEKDAYS.map((wd) => (
          <div key={wd} className={styles.weekdayHeader}>
            {wd}
          </div>
        ))}
        {monthDays.map((day) => {
          const dateKey = day.format('YYYY-MM-DD')
          const events = schedulesByDate.get(dateKey) ?? []
          const isCurrentMonth = day.month() === selectedDate.month()
          const isToday = day.isSame(today, 'day')
          const isSelected = day.isSame(selectedDate, 'day')
          const displayEvents = events.slice(0, MAX_EVENTS_DISPLAY)
          const remaining = events.length - MAX_EVENTS_DISPLAY

          const cellClass = [
            styles.dayCell,
            !isCurrentMonth ? styles.otherMonth : '',
            isToday ? styles.today : '',
            isSelected ? styles.selected : '',
          ]
            .filter(Boolean)
            .join(' ')

          return (
            <div key={dateKey} className={cellClass} onClick={() => onDateClick(day)}>
              <span className={`${styles.dayNumber} ${isToday ? styles.today : ''}`}>
                {day.date()}
              </span>
              <div className={styles.eventsList}>
                {displayEvents.map((evt) => (
                  <EventCard key={evt.id} event={evt} onClick={onEventClick} />
                ))}
                {remaining > 0 && (
                  <span
                    className={styles.moreLink}
                    onClick={(e) => {
                      e.stopPropagation()
                      onDateSelect(day)
                      onViewModeChange('day')
                    }}
                  >
                    +{remaining} 更多
                  </span>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )

  // ─── 周视图 / 日视图 ──────────────────────────────

  const weekDays = useMemo(() => {
    if (viewMode === 'day') return [selectedDate]
    const start = selectedDate.startOf('week')
    return Array.from({ length: 7 }, (_, i) => start.add(i, 'day'))
  }, [selectedDate, viewMode])

  const getEventsForHour = useCallback(
    (day: Dayjs, hour: number): Schedule[] => {
      const dateKey = day.format('YYYY-MM-DD')
      const events = schedulesByDate.get(dateKey) ?? []
      return events.filter((e) => {
        if (e.is_all_day) return hour === 0
        const h = dayjs(e.start_time).hour()
        return h === hour
      })
    },
    [schedulesByDate]
  )

  const getEventTopAndHeight = useCallback((event: Schedule): { top: number; height: number } => {
    const start = dayjs(event.start_time)
    const end = dayjs(event.end_time)
    const top = (start.hour() + start.minute() / 60) * 60
    const durationHours = end.diff(start, 'minute') / 60
    const height = Math.max(durationHours * 60, 20)
    return { top, height }
  }, [])

  const renderTimeGridView = () => (
    <div style={{ display: 'flex', flex: 1 }}>
      {/* 时间列 */}
      <div className={styles.timeLabels}>
        {HOURS.map((h) => (
          <div key={h} className={styles.timeLabel}>
            {h === 0 ? '' : `${h.toString().padStart(2, '0')}:00`}
          </div>
        ))}
      </div>

      {/* 每天一列 */}
      {weekDays.map((day) => {
        const dateKey = day.format('YYYY-MM-DD')
        const dayEvents = schedulesByDate.get(dateKey) ?? []
        const isToday = day.isSame(today, 'day')

        return (
          <div
            key={dateKey}
            style={{
              flex: 1,
              position: 'relative',
              borderLeft: '1px solid var(--color-border-secondary, #f0f0f0)',
            }}
          >
            {/* 日期头部 */}
            <div
              style={{
                textAlign: 'center',
                padding: '8px 4px',
                borderBottom: '1px solid var(--color-border-secondary, #f0f0f0)',
                background: isToday ? 'var(--color-primary-bg, #fff7ed)' : 'transparent',
              }}
            >
              <div style={{ fontSize: 11, color: 'var(--color-text-secondary, #999)' }}>
                {WEEKDAYS[day.day()]}
              </div>
              <div
                style={{
                  fontSize: 16,
                  fontWeight: isToday ? 700 : 400,
                  color: isToday ? 'var(--color-primary, #f97316)' : undefined,
                }}
              >
                {day.date()}
              </div>
            </div>

            {/* 时间格子 */}
            <div className={styles.timeContent}>
              {HOURS.map((h) => (
                <div
                  key={h}
                  className={styles.timeSlot}
                  onClick={() => {
                    onDateClick(day.hour(h))
                  }}
                />
              ))}

              {/* 事件 */}
              {dayEvents.map((evt) => {
                const { top, height } = getEventTopAndHeight(evt)
                const bgColor = evt.color || '#f97316'
                return (
                  <Tooltip key={evt.id} title={evt.title} placement="right">
                    <div
                      className={styles.timeEvent}
                      style={{
                        top: `${top}px`,
                        height: `${height}px`,
                        backgroundColor: bgColor,
                      }}
                      onClick={(e) => {
                        e.stopPropagation()
                        onEventClick(evt)
                      }}
                    >
                      <div className={styles.timeEventTitle}>{evt.title}</div>
                      {!evt.is_all_day && (
                        <div className={styles.timeEventTime}>
                          {dayjs(evt.start_time).format('HH:mm')} -{' '}
                          {dayjs(evt.end_time).format('HH:mm')}
                        </div>
                      )}
                    </div>
                  </Tooltip>
                )
              })}
            </div>
          </div>
        )
      })}
    </div>
  )

  return (
    <div className={styles.calendarContainer}>
      {/* 导航栏 */}
      <div className={styles.navBar}>
        <Button icon={<CalendarOutlined />} onClick={onToday}>
          今天
        </Button>

        <div className={styles.navCenter}>
          <Button type="text" icon={<LeftOutlined />} onClick={onPrev} />
          <span className={styles.navLabel}>
            {selectedDate.format(
              viewMode === 'month'
                ? 'YYYY 年 M 月'
                : viewMode === 'week'
                  ? 'YYYY 年 M 月'
                  : 'YYYY 年 M 月 D 日'
            )}
          </span>
          <Button type="text" icon={<RightOutlined />} onClick={onNext} />
        </div>

        <Segmented
          value={viewMode}
          onChange={(val) => onViewModeChange(val as CalendarViewMode)}
          options={[
            { label: '月', value: 'month' },
            { label: '周', value: 'week' },
            { label: '日', value: 'day' },
          ]}
          size="small"
        />
      </div>

      {/* 日历内容 */}
      {viewMode === 'month' ? renderMonthView() : renderTimeGridView()}
    </div>
  )
})
