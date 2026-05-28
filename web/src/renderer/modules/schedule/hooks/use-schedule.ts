/** 日程 CRUD 状态 hook（TanStack Query） */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useCallback, useState, useMemo, useEffect } from 'react'
import dayjs from 'dayjs'
import isBetween from 'dayjs/plugin/isBetween'
import type { Schedule } from '@/types'
import type { ScheduleFormInput, ScheduleQueryParams, ScheduleByDate } from '../types/schedule'
import {
  fetchSchedules,
  createSchedule,
  updateSchedule,
  deleteSchedule,
} from '../services/schedule-api'
import { pollingRegistry } from '@/services/polling-registry'
import { showUndoToast } from '@/utils/undo-toast'
import { useAppStore } from '@/stores/use-app-store'

dayjs.extend(isBetween)

const QUERY_KEY = ['schedules']

export interface UseScheduleReturn {
  /** 日程列表 */
  schedules: Schedule[]
  /** 按日期分组的日程 */
  schedulesByDate: ScheduleByDate
  /** 加载中 */
  isLoading: boolean
  /** 错误 */
  error: Error | null
  /** 筛选关键词 */
  keyword: string
  setKeyword: (kw: string) => void
  /** 日期范围筛选 */
  queryParams: ScheduleQueryParams
  setQueryParams: (params: ScheduleQueryParams) => void
  /** 创建日程 */
  createScheduleMut: (input: ScheduleFormInput) => Promise<Schedule>
  /** 更新日程 */
  updateScheduleMut: (id: string, input: ScheduleFormInput) => Promise<Schedule>
  /** 删除日程 */
  deleteScheduleMut: (id: string) => Promise<void>
  /** 获取指定日期的日程 */
  getSchedulesForDate: (date: string) => Schedule[]
  /** 获取即将提醒的事件（未来 N 分钟内） */
  upcomingReminders: Schedule[]
  /** 是否有正在提交的操作 */
  isMutating: boolean
}

export function useSchedule(rangeStart?: string, rangeEnd?: string): UseScheduleReturn {
  const queryClient = useQueryClient()
  const [keyword, setKeyword] = useState('')
  const [queryParams, setQueryParams] = useState<ScheduleQueryParams>({})

  const params: ScheduleQueryParams = useMemo(
    () => ({
      startDate: rangeStart,
      endDate: rangeEnd,
      keyword: keyword || undefined,
      ...queryParams,
    }),
    [rangeStart, rangeEnd, keyword, queryParams]
  )

  // 查询
  const {
    data: schedules = [],
    isLoading,
    error,
  } = useQuery({
    queryKey: [...QUERY_KEY, params],
    queryFn: () => fetchSchedules(params),
  })

  // 创建
  const createMut = useMutation({
    mutationFn: (input: ScheduleFormInput) => createSchedule(input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: QUERY_KEY })
    },
  })

  // 更新
  const updateMut = useMutation({
    mutationFn: ({ id, input }: { id: string; input: ScheduleFormInput }) =>
      updateSchedule(id, input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: QUERY_KEY })
    },
  })

  // 删除
  const deleteMut = useMutation({
    mutationFn: (id: string) => deleteSchedule(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: QUERY_KEY })
    },
  })

  const createScheduleMut = useCallback(
    (input: ScheduleFormInput) => createMut.mutateAsync(input),
    [createMut]
  )

  const updateScheduleMut = useCallback(
    (id: string, input: ScheduleFormInput) => updateMut.mutateAsync({ id, input }),
    [updateMut]
  )

  const deleteScheduleMut = useCallback(
    (id: string) => {
      const schedule = schedules.find((s) => s.id === id)
      const title = schedule?.title ?? '日程'
      return deleteMut.mutateAsync(id).then(() => {
        showUndoToast(`已删除「${title}」`, () => {
          // 撤销：重新创建（简化处理，触发 refetch）
          void queryClient.invalidateQueries({ queryKey: QUERY_KEY })
        })
      })
    },
    [deleteMut, schedules, queryClient]
  )

  // 按日期分组
  const schedulesByDate = useMemo(() => {
    const map: ScheduleByDate = new Map()
    for (const s of schedules) {
      const key = dayjs(s.startTime).format('YYYY-MM-DD')
      const list = map.get(key) ?? []
      list.push(s)
      map.set(key, list)
    }
    return map
  }, [schedules])

  // 获取指定日期的日程
  const getSchedulesForDate = useCallback(
    (date: string) => schedulesByDate.get(date) ?? [],
    [schedulesByDate]
  )

  // 即将提醒的事件（未来 30 分钟内有 reminder 的事件）
  const upcomingReminders = useMemo(() => {
    const now = dayjs()
    const threshold = now.add(30, 'minute')
    return schedules.filter((s) => {
      if (s.reminderMinutes <= 0) return false
      const reminderTime = dayjs(s.startTime).subtract(s.reminderMinutes, 'minute')
      return reminderTime.isBetween(now, threshold, null, '[]')
    })
  }, [schedules])

  const isMutating = createMut.isPending || updateMut.isPending || deleteMut.isPending

  // 轮询：定期刷新日程列表
  const pollingEnabled = useAppStore((s) => s.pollingEnabled)
  useEffect(() => {
    const POLLING_ID = 'schedule:list'
    if (pollingEnabled) {
      pollingRegistry.register({
        id: POLLING_ID,
        module: 'schedule',
        interval: 30_000,
        callback: () => queryClient.invalidateQueries({ queryKey: QUERY_KEY }),
        enabled: true,
      })
    }
    return () => {
      pollingRegistry.unregister(POLLING_ID)
    }
  }, [pollingEnabled, queryClient])

  return {
    schedules,
    schedulesByDate,
    isLoading,
    error: error as Error | null,
    keyword,
    setKeyword,
    queryParams,
    setQueryParams,
    createScheduleMut,
    updateScheduleMut,
    deleteScheduleMut,
    getSchedulesForDate,
    upcomingReminders,
    isMutating,
  }
}
