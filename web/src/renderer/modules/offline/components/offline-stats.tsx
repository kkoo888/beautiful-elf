/** 离线存储统计组件 */

import { useState, useEffect, useCallback } from 'react'
import { Card, Statistic, Button, message, Popconfirm, Space } from 'antd'
import { DeleteOutlined, InboxOutlined } from '@ant-design/icons'
import type { OfflineStorageStats } from '../types/offline'
import { getStorageStats, clearAll } from '../services/offline-storage'
import { formatFileSize } from '@/utils'

export function OfflineStats() {
  const [stats, setStats] = useState<OfflineStorageStats>({ count: 0, sizeBytes: 0 })
  const [loading, setLoading] = useState(false)

  const loadStats = useCallback(async () => {
    try {
      const s = await getStorageStats()
      setStats(s)
    } catch {
      // 忽略
    }
  }, [])

  useEffect(() => {
    void loadStats()
  }, [loadStats])

  const handleClear = useCallback(async () => {
    setLoading(true)
    try {
      await clearAll()
      await loadStats()
      void message.success('离线数据已清除')
    } catch {
      void message.error('清除失败')
    } finally {
      setLoading(false)
    }
  }, [loadStats])

  return (
    <Card size="small">
      <Space size="large">
        <Statistic title="待发送消息" value={stats.count} suffix="条" />
        <Statistic title="存储大小" value={formatFileSize(stats.sizeBytes)} />
      </Space>
      <div style={{ marginTop: 12 }}>
        <Popconfirm title="确定清除所有离线数据？" onConfirm={() => void handleClear}>
          <Button
            danger
            icon={<DeleteOutlined />}
            size="small"
            loading={loading}
            disabled={stats.count === 0}
          >
            清除离线数据
          </Button>
        </Popconfirm>
      </div>
    </Card>
  )
}
