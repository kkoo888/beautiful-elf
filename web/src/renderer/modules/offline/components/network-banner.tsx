/** 网络状态横幅（公共组件，可被其他模块引用） */

import { Alert } from 'antd'
import { useNetworkStatus } from '../hooks/use-network-status'
import { useOfflineQueue } from '../hooks/use-offline-queue'

export function NetworkBanner() {
  const { flushQueue } = useOfflineQueue()
  const { isOnline, wasOffline, status } = useNetworkStatus(() => {
    // 网络恢复时自动刷新离线队列
    void flushQueue()
  })

  // 在线且无离线历史 → 不显示
  if (isOnline && !wasOffline) return null

  if (!isOnline) {
    return (
      <Alert
        message="网络已断开"
        description="消息将在网络恢复后自动发送"
        type="warning"
        showIcon
        banner
        closable={false}
      />
    )
  }

  if (status === 'syncing') {
    return (
      <Alert
        message="网络已恢复，正在同步..."
        type="info"
        showIcon
        banner
        closable={false}
      />
    )
  }

  return null
}
