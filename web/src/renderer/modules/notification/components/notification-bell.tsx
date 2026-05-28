/**
 * 通知铃铛组件（未读数角标）
 */

import { Badge } from 'antd'
import { BellOutlined } from '@ant-design/icons'
import { useNotificationStore } from '@/stores/use-notification-store'

interface NotificationBellProps {
  onClick?: () => void
}

export function NotificationBell({ onClick }: NotificationBellProps) {
  const unreadCount = useNotificationStore((s) => s.unreadCount)

  return (
    <Badge count={unreadCount} size="small" offset={[-2, 2]}>
      <BellOutlined
        style={{ fontSize: 20, cursor: 'pointer' }}
        onClick={onClick}
      />
    </Badge>
  )
}
