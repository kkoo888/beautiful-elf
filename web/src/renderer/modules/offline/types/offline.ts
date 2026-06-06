/** 离线模块类型定义 */

/** 离线消息状态 */
export type OfflineMessageStatus = 'pending' | 'sending' | 'failed'

/** 离线消息 */
export interface OfflineMessage {
  id: string
  conversationId: string
  content: string
  createdAt: number
  status: OfflineMessageStatus
  retryCount: number
}

/** 网络状态 */
export type NetworkStatusType = 'online' | 'offline' | 'syncing'

/** 离线存储统计 */
export interface OfflineStorageStats {
  count: number
  sizeBytes: number
}
