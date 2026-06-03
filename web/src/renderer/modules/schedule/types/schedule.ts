/** 日程模块类型定义 */

import type { Schedule } from '@/types'

/** 日程颜色标签预设 */
export const SCHEDULE_COLORS = [
  { label: '默认', value: '#f97316' },
  { label: '蓝色', value: '#3b82f6' },
  { label: '绿色', value: '#22c55e' },
  { label: '红色', value: '#ef4444' },
  { label: '紫色', value: '#a855f7' },
  { label: '粉色', value: '#ec4899' },
  { label: '青色', value: '#06b6d4' },
  { label: '灰色', value: '#6b7280' },
] as const

/** 提醒时间选项（分钟） */
export const REMINDER_OPTIONS = [
  { label: '不提醒', value: 0 },
  { label: '5 分钟前', value: 5 },
  { label: '10 分钟前', value: 10 },
  { label: '15 分钟前', value: 15 },
  { label: '30 分钟前', value: 30 },
  { label: '1 小时前', value: 60 },
  { label: '1 天前', value: 1440 },
] as const

/** 日历视图模式 */
export type CalendarViewMode = 'month' | 'week' | 'day'

/** 日程表单输入（前端统一 camelCase，后端 CamelModel 已支持） */
export interface ScheduleFormInput {
  title: string
  description?: string
  startTime: Date
  endTime: Date
  isAllDay: boolean
  reminderMinutes: number
  color?: string
  repeat: 'none' | 'daily' | 'weekly' | 'monthly'
}

/** 日程列表查询参数 */
export interface ScheduleQueryParams {
  startDate?: string
  endDate?: string
  keyword?: string
}

/** 按日期分组的日程映射 */
export type ScheduleByDate = Map<string, Schedule[]>
