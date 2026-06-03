/**
 * 通知 API 服务
 *
 * 后端 CamelModel 已统一返回 camelCase，直接透传。
 */

import { apiClient } from '@/services/api-client'
import type { Notification, NotificationType } from '../types/notification'

/** 通知列表查询参数 */
export interface NotificationListParams {
  page?: number
  pageSize?: number
  type?: NotificationType
  isRead?: 0 | 1
}

/** 通知列表响应 */
export interface NotificationListResponse {
  data: Notification[]
  total: number
  page: number
  pageSize: number
}

/** 创建通知参数 */
export interface CreateNotificationParams {
  eventId?: string
  type: NotificationType
  title: string
  message: string
  actionUrl?: string
}

/** 获取通知列表 */
export async function fetchNotifications(params?: NotificationListParams): Promise<NotificationListResponse> {
  const resp = await apiClient.get('/notifications', { params })
  return (resp.data as any).data
}

/** 创建通知 */
export async function createNotification(data: CreateNotificationParams): Promise<Notification> {
  const resp = await apiClient.post('/notifications', data)
  return (resp.data as any).data
}

/** 删除通知 */
export async function deleteNotification(id: string): Promise<void> {
  await apiClient.delete(`/notifications/${id}`)
}

/** 标记单条通知已读 */
export async function markRead(id: string): Promise<void> {
  await apiClient.put(`/notifications/${id}/read`)
}

/** 标记全部通知已读 */
export async function markAllRead(): Promise<void> {
  await apiClient.put('/notifications/read-all')
}
