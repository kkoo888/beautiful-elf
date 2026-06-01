/** 日程 API 服务（mock 实现，后续替换为真实 API） */

import { apiClient } from '@/services/api-client'
import type { Schedule } from '@/types'
import type { ScheduleFormInput, ScheduleQueryParams } from '../types/schedule'
import { generateId } from '@/utils'

// ─── Mock 数据 ────────────────────────────────────────────

const now = new Date()
const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())

function iso(d: Date): string {
  return d.toISOString()
}

const mockSchedules: Schedule[] = [
  {
    id: generateId(),
    title: '团队周会',
    description: '每周例会，讨论本周进展和下周计划',
    startTime: iso(new Date(today.getTime() + 10 * 3600_000)),
    endTime: iso(new Date(today.getTime() + 11 * 3600_000)),
    allDay: 0,
    reminderMinutes: 15,
    color: '#3b82f6',
    repeatType: 2,
    deleted: 0,
    createdAt: iso(new Date(today.getTime() - 7 * 86400_000)),
    updatedAt: iso(today),
  },
  {
    id: generateId(),
    title: '项目截止日',
    description: 'Beautiful-Elf v0.2 里程碑截止',
    startTime: iso(new Date(today.getTime() + 3 * 86400_000)),
    endTime: iso(new Date(today.getTime() + 3 * 86400_000 + 86400_000)),
    allDay: 1,
    reminderMinutes: 1440,
    color: '#ef4444',
    repeatType: 0,
    deleted: 0,
    createdAt: iso(new Date(today.getTime() - 14 * 86400_000)),
    updatedAt: iso(today),
  },
  {
    id: generateId(),
    title: '午餐约会',
    description: '和朋友一起吃饭',
    startTime: iso(new Date(today.getTime() + 12 * 3600_000)),
    endTime: iso(new Date(today.getTime() + 13 * 3600_000)),
    allDay: 0,
    reminderMinutes: 30,
    color: '#22c55e',
    repeatType: 0,
    deleted: 0,
    createdAt: iso(new Date(today.getTime() - 86400_000)),
    updatedAt: iso(today),
  },
  {
    id: generateId(),
    title: '阅读时间',
    startTime: iso(new Date(today.getTime() + 20 * 3600_000)),
    endTime: iso(new Date(today.getTime() + 21 * 3600_000)),
    allDay: 0,
    reminderMinutes: 10,
    color: '#a855f7',
    repeatType: 1,
    deleted: 0,
    createdAt: iso(new Date(today.getTime() - 30 * 86400_000)),
    updatedAt: iso(today),
  },
  {
    id: generateId(),
    title: '代码 Review',
    startTime: iso(new Date(today.getTime() + 86400_000 + 14 * 3600_000)),
    endTime: iso(new Date(today.getTime() + 86400_000 + 15 * 3600_000)),
    allDay: 0,
    reminderMinutes: 5,
    color: '#06b6d4',
    repeatType: 0,
    deleted: 0,
    createdAt: iso(today),
    updatedAt: iso(today),
  },
  {
    id: generateId(),
    title: '健身',
    startTime: iso(new Date(today.getTime() + 86400_000 + 18 * 3600_000)),
    endTime: iso(new Date(today.getTime() + 86400_000 + 19.5 * 3600_000)),
    allDay: 0,
    reminderMinutes: 30,
    color: '#ec4899',
    repeatType: 1,
    deleted: 0,
    createdAt: iso(new Date(today.getTime() - 30 * 86400_000)),
    updatedAt: iso(today),
  },
  {
    id: generateId(),
    title: '产品评审会议',
    startTime: iso(new Date(today.getTime() + 2 * 86400_000 + 10 * 3600_000)),
    endTime: iso(new Date(today.getTime() + 2 * 86400_000 + 12 * 3600_000)),
    allDay: 0,
    reminderMinutes: 60,
    color: '#f97316',
    repeatType: 0,
    deleted: 0,
    createdAt: iso(today),
    updatedAt: iso(today),
  },
  {
    id: generateId(),
    title: '生日派对',
    startTime: iso(new Date(today.getTime() + 5 * 86400_000)),
    endTime: iso(new Date(today.getTime() + 5 * 86400_000 + 86400_000)),
    allDay: 1,
    reminderMinutes: 1440,
    color: '#ec4899',
    repeatType: 0,
    deleted: 0,
    createdAt: iso(today),
    updatedAt: iso(today),
  },
]

let mockStore = [...mockSchedules]

function delay(ms = 300): Promise<void> {
  return new Promise((r) => setTimeout(r, ms))
}

// ─── API 函数 ─────────────────────────────────────────────

/** 获取日程列表 */
export async function fetchSchedules(params?: ScheduleQueryParams): Promise<Schedule[]> {
  await delay()
  // 尝试真实 API，失败则用 mock
  try {
    const { data } = await apiClient.get('/schedules', { params })
    return (data as { data: Schedule[] }).data
  } catch {
    let result = mockStore.filter((s) => !s.isDeleted)

    if (params?.startDate) {
      const start = new Date(params.startDate).getTime()
      result = result.filter((s) => new Date(s.endTime).getTime() >= start)
    }
    if (params?.endDate) {
      const end = new Date(params.endDate).getTime()
      result = result.filter((s) => new Date(s.startTime).getTime() <= end)
    }
    if (params?.keyword) {
      const kw = params.keyword.toLowerCase()
      result = result.filter(
        (s) =>
          s.title.toLowerCase().includes(kw) || (s.description?.toLowerCase().includes(kw) ?? false)
      )
    }
    return result
  }
}

/** 创建日程 */
export async function createSchedule(input: ScheduleFormInput): Promise<Schedule> {
  await delay()
  try {
    const { data } = await apiClient.post('/schedules', input)
    return (data as { data: Schedule }).data
  } catch {
    const schedule: Schedule = {
      id: generateId(),
      title: input.title,
      description: input.description,
      startTime: input.startTime.toISOString(),
      endTime: input.endTime.toISOString(),
      allDay: input.isAllDay ? 1 : 0,
      reminderMinutes: input.reminderMinutes,
      color: input.color,
      repeatType: input.repeat === 'daily' ? 1 : input.repeat === 'weekly' ? 2 : input.repeat === 'monthly' ? 3 : 0,
      deleted: 0,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    }
    mockStore.push(schedule)
    return schedule
  }
}

/** 更新日程 */
export async function updateSchedule(id: string, input: ScheduleFormInput): Promise<Schedule> {
  await delay()
  try {
    const { data } = await apiClient.put(`/schedules/${id}`, input)
    return (data as { data: Schedule }).data
  } catch {
    const idx = mockStore.findIndex((s) => s.id === id)
    if (idx === -1) throw new Error('Schedule not found')
    const updated: Schedule = {
      ...mockStore[idx],
      title: input.title,
      description: input.description,
      startTime: input.startTime.toISOString(),
      endTime: input.endTime.toISOString(),
      allDay: input.isAllDay ? 1 : 0,
      reminderMinutes: input.reminderMinutes,
      color: input.color,
      repeatType: input.repeat === 'daily' ? 1 : input.repeat === 'weekly' ? 2 : input.repeat === 'monthly' ? 3 : 0,
      updatedAt: new Date().toISOString(),
    }
    mockStore[idx] = updated
    return updated
  }
}

/** 删除日程（软删除） */
export async function deleteSchedule(id: string): Promise<void> {
  await delay()
  try {
    await apiClient.delete(`/schedules/${id}`)
  } catch {
    const idx = mockStore.findIndex((s) => s.id === id)
    if (idx !== -1) {
      mockStore[idx] = { ...mockStore[idx], deleted: 1, updatedAt: new Date().toISOString() }
    }
  }
}
