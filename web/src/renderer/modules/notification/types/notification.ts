/**
 * 通知类型定义
 */

/** 通知类型 */
export type NotificationType =
  | 'schedule' // 📅 日程提醒
  | 'workflow' // ⚙️ 工作流（完成/失败）
  | 'subagent' // 🤖 子代理（完成/失败）
  | 'skill_suggest' // 💡 技能建议
  | 'system_alert' // 📊 系统告警

/** 通知类型图标映射 */
export const NOTIFICATION_TYPE_ICON: Record<NotificationType, string> = {
  schedule: '📅',
  workflow: '⚙️',
  subagent: '🤖',
  skill_suggest: '💡',
  system_alert: '📊',
}

/** 通知类型名称映射 */
export const NOTIFICATION_TYPE_LABEL: Record<NotificationType, string> = {
  schedule: '日程提醒',
  workflow: '工作流',
  subagent: '子代理',
  skill_suggest: '技能建议',
  system_alert: '系统告警',
}

/** 通知数据（与 @/types Notification 对齐，额外支持 eventId 去重） */
export interface Notification {
  id: string
  eventId?: string
  type: NotificationType
  title: string
  message: string
  read: boolean
  created_at: string
  action_url?: string
}

/** 通知弹窗消息格式（用于 showNotification） */
export interface NotificationMessage {
  id: string
  eventId?: string
  type: NotificationType
  title: string
  body: string
  read: boolean
  createdAt: number
}

/** 通知筛选条件 */
export interface NotificationFilter {
  type?: NotificationType | 'all'
  read?: 'all' | 'read' | 'unread'
}
