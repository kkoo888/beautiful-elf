/** 日程主面板 */

import { useState, useCallback, useMemo, useEffect } from 'react'
import { Button, Input, Spin, Empty, Badge } from 'antd'
import { PlusOutlined, SearchOutlined, BellOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import type { Schedule } from '@/types'
import { useCalendar } from '../hooks/use-calendar'
import { useSchedule } from '../hooks/use-schedule'
import { CalendarView } from './calendar-view'
import { EventForm } from './event-form'
import { EventDetail } from './event-detail'
import type { ScheduleFormInput } from '../types/schedule'
import styles from './schedule-panel.module.css'

const { Search } = Input

export function SchedulePanel() {
  const calendar = useCalendar()

  // 响应式：窄屏自动切换为日视图
  useEffect(() => {
    const mq = window.matchMedia('(max-width: 768px)')
    const handler = (e: MediaQueryListEvent | MediaQueryList) => {
      if (e.matches && calendar.viewMode === 'month') {
        calendar.setViewMode('day')
      }
    }
    handler(mq)
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const {
    schedules,
    schedulesByDate,
    isLoading,
    keyword,
    setKeyword,
    createScheduleMut,
    updateScheduleMut,
    deleteScheduleMut,
    upcomingReminders,
    isMutating,
  } = useSchedule(calendar.rangeStart, calendar.rangeEnd)

  // 表单状态
  const [formOpen, setFormOpen] = useState(false)
  const [editingEvent, setEditingEvent] = useState<Schedule | null>(null)
  const [initialDate, setInitialDate] = useState<dayjs.Dayjs | undefined>()

  // 详情弹窗
  const [detailOpen, setDetailOpen] = useState(false)
  const [selectedEvent, setSelectedEvent] = useState<Schedule | null>(null)

  // ─── 事件处理 ──────────────────────────────────────

  const handleCreate = useCallback((date?: dayjs.Dayjs) => {
    setEditingEvent(null)
    setInitialDate(date)
    setFormOpen(true)
  }, [])

  const handleEdit = useCallback((event: Schedule) => {
    setDetailOpen(false)
    setEditingEvent(event)
    setInitialDate(undefined)
    setFormOpen(true)
  }, [])

  const handleEventClick = useCallback((event: Schedule) => {
    setSelectedEvent(event)
    setDetailOpen(true)
  }, [])

  const handleDateClick = useCallback(
    (date: dayjs.Dayjs) => {
      calendar.setSelectedDate(date)
      handleCreate(date)
    },
    [calendar, handleCreate]
  )

  const handleFormSubmit = useCallback(
    async (data: ScheduleFormInput) => {
      if (editingEvent) {
        await updateScheduleMut(editingEvent.id, data)
      } else {
        await createScheduleMut(data)
      }
    },
    [editingEvent, createScheduleMut, updateScheduleMut]
  )

  const handleDelete = useCallback(
    async (id: string) => {
      await deleteScheduleMut(id)
    },
    [deleteScheduleMut]
  )

  // 即将提醒的事件数
  const reminderCount = upcomingReminders.length

  return (
    <div className={styles.panel}>
      {/* 头部 */}
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <h2 className={styles.title}>📅 日程</h2>
          {reminderCount > 0 && (
            <Badge count={reminderCount} size="small">
              <BellOutlined style={{ fontSize: 18, color: '#d97706' }} />
            </Badge>
          )}
        </div>

        <div className={styles.headerActions}>
          <Search
            className={styles.searchInput}
            placeholder="搜索日程..."
            allowClear
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            prefix={<SearchOutlined />}
            size="small"
          />
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => handleCreate()}
            loading={isMutating}
          >
            新建
          </Button>
        </div>
      </div>

      {/* 日历视图 */}
      {isLoading ? (
        <div className={styles.loading}>
          <Spin size="large" />
        </div>
      ) : (
        <CalendarView
          viewMode={calendar.viewMode}
          selectedDate={calendar.selectedDate}
          today={calendar.today}
          schedules={schedules}
          schedulesByDate={schedulesByDate}
          onDateSelect={calendar.setSelectedDate}
          onViewModeChange={calendar.setViewMode}
          onPrev={calendar.goPrev}
          onNext={calendar.goNext}
          onToday={calendar.goToToday}
          onEventClick={handleEventClick}
          onDateClick={handleDateClick}
        />
      )}

      {/* 创建/编辑表单 */}
      <EventForm
        open={formOpen}
        onClose={() => setFormOpen(false)}
        onSubmit={handleFormSubmit}
        editingEvent={editingEvent}
        initialDate={initialDate}
      />

      {/* 详情弹窗 */}
      <EventDetail
        open={detailOpen}
        event={selectedEvent}
        onClose={() => setDetailOpen(false)}
        onEdit={handleEdit}
        onDelete={(id) => void handleDelete(id)}
      />
    </div>
  )
}
