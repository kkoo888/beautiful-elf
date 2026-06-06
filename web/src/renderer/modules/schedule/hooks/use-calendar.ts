/** 日历导航状态 hook */

import { useState, useCallback, useMemo } from 'react'
import dayjs, { type Dayjs } from 'dayjs'
import type { CalendarViewMode } from '../types/schedule'

export interface UseCalendarReturn {
  /** 当前选中日期 */
  selectedDate: Dayjs
  /** 当前视图模式 */
  viewMode: CalendarViewMode
  /** 设置选中日期 */
  setSelectedDate: (date: Dayjs) => void
  /** 切换视图模式 */
  setViewMode: (mode: CalendarViewMode) => void
  /** 今天 */
  today: Dayjs
  /** 跳到今天 */
  goToToday: () => void
  /** 前进（月/周/天） */
  goNext: () => void
  /** 后退（月/周/天） */
  goPrev: () => void
  /** 当前显示范围的文字描述 */
  rangeLabel: string
  /** 当前月/周/日的起止时间（ISO 字符串） */
  rangeStart: string
  rangeEnd: string
}

export function useCalendar(): UseCalendarReturn {
  const [selectedDate, setSelectedDate] = useState<Dayjs>(dayjs())
  const [viewMode, setViewMode] = useState<CalendarViewMode>('month')
  const today = useMemo(() => dayjs(), [])

  const goToToday = useCallback(() => {
    setSelectedDate(dayjs())
  }, [])

  const goNext = useCallback(() => {
    setSelectedDate((prev) => {
      switch (viewMode) {
        case 'month':
          return prev.add(1, 'month')
        case 'week':
          return prev.add(1, 'week')
        case 'day':
          return prev.add(1, 'day')
      }
    })
  }, [viewMode])

  const goPrev = useCallback(() => {
    setSelectedDate((prev) => {
      switch (viewMode) {
        case 'month':
          return prev.subtract(1, 'month')
        case 'week':
          return prev.subtract(1, 'week')
        case 'day':
          return prev.subtract(1, 'day')
      }
    })
  }, [viewMode])

  const rangeLabel = useMemo(() => {
    switch (viewMode) {
      case 'month':
        return selectedDate.format('YYYY 年 M 月')
      case 'week': {
        const start = selectedDate.startOf('week')
        const end = selectedDate.endOf('week')
        return `${start.format('M/D')} - ${end.format('M/D')}`
      }
      case 'day':
        return selectedDate.format('YYYY 年 M 月 D 日')
    }
  }, [selectedDate, viewMode])

  const rangeStart = useMemo(() => {
    switch (viewMode) {
      case 'month':
        return selectedDate.startOf('month').toISOString()
      case 'week':
        return selectedDate.startOf('week').toISOString()
      case 'day':
        return selectedDate.startOf('day').toISOString()
    }
  }, [selectedDate, viewMode])

  const rangeEnd = useMemo(() => {
    switch (viewMode) {
      case 'month':
        return selectedDate.endOf('month').toISOString()
      case 'week':
        return selectedDate.endOf('week').toISOString()
      case 'day':
        return selectedDate.endOf('day').toISOString()
    }
  }, [selectedDate, viewMode])

  return {
    selectedDate,
    viewMode,
    setSelectedDate,
    setViewMode,
    today,
    goToToday,
    goNext,
    goPrev,
    rangeLabel,
    rangeStart,
    rangeEnd,
  }
}
