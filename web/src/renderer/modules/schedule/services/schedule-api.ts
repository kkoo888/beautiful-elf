/**
 * 日程 API 服务
 * 后端 Query: page, page_size, start_date, end_date, keyword
 */

import { apiClient, extractData } from '@/services/api-client'
import type { Schedule } from '@/types'
import type { ScheduleFormInput, ScheduleQueryParams } from '../types/schedule'
import { generateId } from '@/utils'

const now = new Date()
const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
const iso = (d: Date) => d.toISOString()

const mockSchedules: Schedule[] = [
  { id: generateId(), title: '团队周会', description: '每周例会', startTime: iso(new Date(today.getTime() + 10 * 3600_000)), endTime: iso(new Date(today.getTime() + 11 * 3600_000)), allDay: 0, reminderMinutes: 15, color: '#3b82f6', repeatType: 2, isDeleted: 0, createdAt: iso(new Date(today.getTime() - 7 * 86400_000)), updatedAt: iso(today) },
  { id: generateId(), title: '项目截止日', description: 'v0.2 里程碑', startTime: iso(new Date(today.getTime() + 3 * 86400_000)), endTime: iso(new Date(today.getTime() + 4 * 86400_000)), allDay: 1, reminderMinutes: 1440, color: '#ef4444', repeatType: 0, isDeleted: 0, createdAt: iso(new Date(today.getTime() - 14 * 86400_000)), updatedAt: iso(today) },
  { id: generateId(), title: '午餐约会', startTime: iso(new Date(today.getTime() + 12 * 3600_000)), endTime: iso(new Date(today.getTime() + 13 * 3600_000)), allDay: 0, reminderMinutes: 30, color: '#22c55e', repeatType: 0, isDeleted: 0, createdAt: iso(new Date(today.getTime() - 86400_000)), updatedAt: iso(today) },
  { id: generateId(), title: '阅读时间', startTime: iso(new Date(today.getTime() + 20 * 3600_000)), endTime: iso(new Date(today.getTime() + 21 * 3600_000)), allDay: 0, reminderMinutes: 10, color: '#a855f7', repeatType: 1, isDeleted: 0, createdAt: iso(new Date(today.getTime() - 30 * 86400_000)), updatedAt: iso(today) },
  { id: generateId(), title: '代码 Review', startTime: iso(new Date(today.getTime() + 86400_000 + 14 * 3600_000)), endTime: iso(new Date(today.getTime() + 86400_000 + 15 * 3600_000)), allDay: 0, reminderMinutes: 5, color: '#06b6d4', repeatType: 0, isDeleted: 0, createdAt: iso(today), updatedAt: iso(today) },
  { id: generateId(), title: '健身', startTime: iso(new Date(today.getTime() + 86400_000 + 18 * 3600_000)), endTime: iso(new Date(today.getTime() + 86400_000 + 19.5 * 3600_000)), allDay: 0, reminderMinutes: 30, color: '#ec4899', repeatType: 1, isDeleted: 0, createdAt: iso(new Date(today.getTime() - 30 * 86400_000)), updatedAt: iso(today) },
  { id: generateId(), title: '产品评审', startTime: iso(new Date(today.getTime() + 2 * 86400_000 + 10 * 3600_000)), endTime: iso(new Date(today.getTime() + 2 * 86400_000 + 12 * 3600_000)), allDay: 0, reminderMinutes: 60, color: '#f97316', repeatType: 0, isDeleted: 0, createdAt: iso(today), updatedAt: iso(today) },
  { id: generateId(), title: '生日派对', startTime: iso(new Date(today.getTime() + 5 * 86400_000)), endTime: iso(new Date(today.getTime() + 6 * 86400_000)), allDay: 1, reminderMinutes: 1440, color: '#ec4899', repeatType: 0, isDeleted: 0, createdAt: iso(today), updatedAt: iso(today) },
]

let mockStore = [...mockSchedules]
const delay = (ms = 300) => new Promise<void>((r) => setTimeout(r, ms))

export async function fetchSchedules(params?: ScheduleQueryParams): Promise<Schedule[]> {
  await delay()
  try {
    // 后端 Query: start_date, end_date, keyword
    return extractData(await apiClient.get('/schedules', { params }))
  } catch {
    let result = mockStore.filter((s) => !s.isDeleted)
    if (params?.startDate) { const s = new Date(params.startDate).getTime(); result = result.filter((r) => new Date(r.endTime).getTime() >= s) }
    if (params?.endDate) { const e = new Date(params.endDate).getTime(); result = result.filter((r) => new Date(r.startTime).getTime() <= e) }
    if (params?.keyword) { const kw = params.keyword.toLowerCase(); result = result.filter((r) => r.title.toLowerCase().includes(kw) || (r.description?.toLowerCase().includes(kw) ?? false)) }
    return result
  }
}

export async function createSchedule(input: ScheduleFormInput): Promise<Schedule> {
  await delay()
  try { return extractData(await apiClient.post('/schedules', input)) }
  catch {
    const schedule: Schedule = {
      id: generateId(), title: input.title, description: input.description,
      startTime: input.startTime.toISOString(), endTime: input.endTime.toISOString(),
      allDay: input.isAllDay ? 1 : 0, reminderMinutes: input.reminderMinutes, color: input.color,
      repeatType: input.repeat === 'daily' ? 1 : input.repeat === 'weekly' ? 2 : input.repeat === 'monthly' ? 3 : 0,
      isDeleted: 0, createdAt: new Date().toISOString(), updatedAt: new Date().toISOString(),
    }
    mockStore.push(schedule)
    return schedule
  }
}

export async function updateSchedule(id: string, input: ScheduleFormInput): Promise<Schedule> {
  await delay()
  try { return extractData(await apiClient.put(`/schedules/${id}`, input)) }
  catch {
    const idx = mockStore.findIndex((s) => s.id === id)
    if (idx === -1) throw new Error('Schedule not found')
    mockStore[idx] = {
      ...mockStore[idx], title: input.title, description: input.description,
      startTime: input.startTime.toISOString(), endTime: input.endTime.toISOString(),
      allDay: input.isAllDay ? 1 : 0, reminderMinutes: input.reminderMinutes, color: input.color,
      repeatType: input.repeat === 'daily' ? 1 : input.repeat === 'weekly' ? 2 : input.repeat === 'monthly' ? 3 : 0,
      updatedAt: new Date().toISOString(),
    }
    return mockStore[idx]
  }
}

export async function deleteSchedule(id: string): Promise<void> {
  await delay()
  try { await apiClient.delete(`/schedules/${id}`) }
  catch {
    const idx = mockStore.findIndex((s) => s.id === id)
    if (idx !== -1) mockStore[idx] = { ...mockStore[idx], isDeleted: 1, updatedAt: new Date().toISOString() }
  }
}
