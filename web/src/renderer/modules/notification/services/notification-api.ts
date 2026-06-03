/**
 * 通知 API 服务
 * 后端 Query: page, page_size, type, is_read
 */

import { apiClient, extractData } from '@/services/api-client'
import type { Notification, NotificationType } from '../types/notification'

export interface NotificationListParams { page?: number; pageSize?: number; type?: NotificationType; isRead?: 0 | 1 }
export interface NotificationListResponse { data: Notification[]; total: number; page: number; pageSize: number }
export interface CreateNotificationParams { eventId?: string; type: NotificationType; title: string; message: string; actionUrl?: string }

export async function fetchNotifications(params?: NotificationListParams): Promise<NotificationListResponse> {
  return extractData(await apiClient.get('/notifications', {
    params: { page: params?.page, page_size: params?.pageSize, type: params?.type, is_read: params?.isRead },
  })) as NotificationListResponse
}

export async function createNotification(data: CreateNotificationParams): Promise<Notification> {
  return extractData(await apiClient.post('/notifications', data))
}

export async function deleteNotification(id: string): Promise<void> {
  await apiClient.delete(`/notifications/${id}`)
}

export async function markRead(id: string): Promise<void> {
  await apiClient.put(`/notifications/${id}/read`)
}

export async function markAllRead(): Promise<void> {
  await apiClient.put('/notifications/read-all')
}
