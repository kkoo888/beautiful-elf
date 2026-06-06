/** 离线存储服务 — 对外 API，委托给 offline-db.ts */

import type { OfflineMessage, OfflineStorageStats } from '../types/offline'
import {
  addMessage,
  getMessages,
  getMessagesByStatus,
  deleteMessage,
  updateMessageStatus,
  clearSent,
  getStorageSize,
} from './offline-db'

/** 保存离线消息 */
export async function saveMessage(msg: OfflineMessage): Promise<void> {
  return addMessage(msg)
}

/** 获取所有待发送消息（按 createdAt 升序） */
export async function getPendingMessages(): Promise<OfflineMessage[]> {
  return getMessagesByStatus('pending')
}

/** 获取所有消息 */
export async function getAllMessages(): Promise<OfflineMessage[]> {
  return getMessages()
}

/** 删除消息 */
export async function removeMessage(id: string): Promise<void> {
  return deleteMessage(id)
}

/** 更新消息发送状态 */
export async function markMessageStatus(
  id: string,
  status: OfflineMessage['status']
): Promise<void> {
  return updateMessageStatus(id, status)
}

/** 清空所有离线数据 */
export async function clearAll(): Promise<void> {
  return clearSent()
}

/** 获取存储统计 */
export async function getStorageStats(): Promise<OfflineStorageStats> {
  return getStorageSize()
}
