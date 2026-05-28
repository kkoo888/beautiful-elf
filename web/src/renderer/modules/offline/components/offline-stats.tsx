/** 离线存储统计组件 */

import { useState, useEffect, useCallback } from 'react'
import { Card, Statistic, Button, message, Popconfirm, Space, Row, Col } from 'antd'
import {
  DeleteOutlined,
  ClockCircleOutlined,
  SyncOutlined,
  CloseCircleOutlined,
  DatabaseOutlined,
} from '@ant-design/icons'
import type { OfflineMessage, OfflineStorageStats } from '../types/offline'
import { getMessages, clearAll, getStorageStats } from '../services/offline-storage'
import { formatFileSize } from '@/utils'

interface StatusCounts {
  pending: number
  sending: number
  failed: number
}

export function OfflineStats() {
  const [stats, setStats] = useState<OfflineStorageStats>({ count: 0, sizeBytes: 0 })
  const [counts, setCounts] = useState<StatusCounts>({ pending: 0, sending: 0, failed: 0 })
  const [loading, setLoading] = useState(false)

  const loadStats = useCallback(async () => {
    try {
      const [s, allMessages] = await Promise.all([getStorageStats(), getMessages()])
      setStats(s)

      const c: StatusCounts = { pending: 0, sending: 0, failed: 0 }
      for (const msg of allMessages as OfflineMessage[]) {
        c[msg.status]++
      }
      setCounts(c)
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
    <Card size="small" title="离线存储统计" extra={<DatabaseOutlined />}>
      <Row gutter={[16, 16]}>
        <Col span={6}>
          <Statistic
            title="待发送"
            value={counts.pending}
            suffix="条"
            prefix={<ClockCircleOutlined />}
            valueStyle={{ color: '#faad14' }}
          />
        </Col>
        <Col span={6}>
          <Statistic
            title="发送中"
            value={counts.sending}
            suffix="条"
            prefix={<SyncOutlined spin={counts.sending > 0} />}
            valueStyle={{ color: '#1677ff' }}
          />
        </Col>
        <Col span={6}>
          <Statistic
            title="失败"
            value={counts.failed}
            suffix="条"
            prefix={<CloseCircleOutlined />}
            valueStyle={{ color: counts.failed > 0 ? '#ff4d4f' : undefined }}
          />
        </Col>
        <Col span={6}>
          <Statistic
            title="存储大小"
            value={formatFileSize(stats.sizeBytes)}
            prefix={<DatabaseOutlined />}
          />
        </Col>
      </Row>
      <div style={{ marginTop: 16 }}>
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
