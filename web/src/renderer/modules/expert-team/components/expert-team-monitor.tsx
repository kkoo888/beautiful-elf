/** 专家团运行记录监控组件 */

import {
  Table,
  Tag,
  Space,
  Button,
  Typography,
  Timeline,
  Card,
  Collapse,
  Empty,
} from 'antd'
import {
  ReloadOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons'
import { useState } from 'react'
import type { ColumnsType } from 'antd/es/table'
import type { ExpertTeamRun, ExpertRunStatus, DiscussionMessage } from '../types'
import { EXPERT_RUN_STATUS_MAP } from '../types'
import { EmptyState } from '@/components/empty-state'

const { Text, Paragraph } = Typography

interface ExpertTeamMonitorProps {
  runs: ExpertTeamRun[]
  loading?: boolean
  onRefresh: () => void
}

export function ExpertTeamMonitor({ runs, loading, onRefresh }: ExpertTeamMonitorProps) {
  const [expandedRunId, setExpandedRunId] = useState<number | null>(null)

  const getStatusIcon = (status: ExpertRunStatus) => {
    switch (status) {
      case 0:
        return <ClockCircleOutlined style={{ color: '#8c8c8c' }} />
      case 1:
        return <LoadingOutlined style={{ color: '#1890ff' }} />
      case 2:
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />
      case 3:
        return <CloseCircleOutlined style={{ color: '#f5222d' }} />
      case 4:
        return <ClockCircleOutlined style={{ color: '#faad14' }} />
    }
  }

  const formatDuration = (ms: number) => {
    if (ms < 1000) return `${ms}ms`
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
    return `${(ms / 60000).toFixed(1)}min`
  }

  const columns: ColumnsType<ExpertTeamRun> = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
      render: (id: number) => <Text code>#{id}</Text>,
    },
    {
      title: '输入',
      dataIndex: 'input_text',
      key: 'input_text',
      ellipsis: true,
      render: (text: string) => (
        <Paragraph ellipsis={{ rows: 1, tooltip: true }} style={{ margin: 0 }}>
          {text}
        </Paragraph>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: ExpertRunStatus) => {
        const { label, color } = EXPERT_RUN_STATUS_MAP[status]
        return (
          <Tag icon={getStatusIcon(status)} color={color}>
            {label}
          </Tag>
        )
      },
    },
    {
      title: '轮次',
      dataIndex: 'round_count',
      key: 'round_count',
      width: 80,
      align: 'center',
      render: (count: number) => <Tag>{count}</Tag>,
    },
    {
      title: '耗时',
      dataIndex: 'duration_ms',
      key: 'duration_ms',
      width: 100,
      render: (ms: number) => (ms ? formatDuration(ms) : '-'),
    },
    {
      title: 'Token',
      dataIndex: 'token_usage',
      key: 'token_usage',
      width: 100,
      render: (tokens: number) => (tokens ? tokens.toLocaleString() : '-'),
    },
    {
      title: '时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (time: string) => (time ? new Date(time).toLocaleString() : '-'),
    },
  ]

  const renderDiscussion = (run: ExpertTeamRun) => {
    if (!run.discussion_json || run.discussion_json.length === 0) {
      return <Empty description="暂无讨论记录" />
    }

    // 按轮次分组
    const rounds = new Map<number, DiscussionMessage[]>()
    for (const msg of run.discussion_json) {
      const roundNum = msg.round
      if (!rounds.has(roundNum)) rounds.set(roundNum, [])
      rounds.get(roundNum)!.push(msg)
    }

    return (
      <Collapse
        size="small"
        items={Array.from(rounds.entries()).map(([roundNum, messages]) => ({
          key: roundNum,
          label: roundNum === 0 ? '🎯 编排器分析' : `💬 第 ${roundNum} 轮讨论`,
          children: (
            <Timeline
              items={messages.map((msg) => ({
                color: msg.expert_role === 'Orchestrator' ? 'blue' : 'green',
                children: (
                  <div>
                    <Space>
                      <Text strong>{msg.expert_name}</Text>
                      <Tag color="geekblue">{msg.expert_role}</Tag>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {new Date(msg.timestamp).toLocaleTimeString()}
                      </Text>
                    </Space>
                    <Paragraph style={{ marginTop: 4, whiteSpace: 'pre-wrap' }}>
                      {msg.content}
                    </Paragraph>
                  </div>
                ),
              }))}
            />
          ),
        }))}
      />
    )
  }

  if (!loading && runs.length === 0) {
    return (
      <EmptyState
        description="暂无运行记录，执行专家团后会在这里显示"
        icon="📊"
      />
    )
  }

  return (
    <div>
      <div style={{ marginBottom: 16, textAlign: 'right' }}>
        <Button icon={<ReloadOutlined />} onClick={onRefresh}>
          刷新
        </Button>
      </div>

      <Table
        columns={columns}
        dataSource={runs}
        rowKey="id"
        loading={loading}
        pagination={{ pageSize: 10 }}
        expandable={{
          expandedRowRender: (record) => (
            <div style={{ padding: '16px 0' }}>
              {/* 输出结果 */}
              {record.output_text && (
                <Card
                  title="📋 最终输出"
                  size="small"
                  style={{ marginBottom: 16 }}
                >
                  <Paragraph style={{ whiteSpace: 'pre-wrap', margin: 0 }}>
                    {record.output_text}
                  </Paragraph>
                </Card>
              )}

              {/* 错误信息 */}
              {record.error_message && (
                <Card
                  title="❌ 错误信息"
                  size="small"
                  style={{ marginBottom: 16 }}
                >
                  <Text type="danger">{record.error_message}</Text>
                </Card>
              )}

              {/* 讨论过程 */}
              <Card title="💬 讨论过程" size="small">
                {renderDiscussion(record)}
              </Card>
            </div>
          ),
          expandedRowKeys: expandedRunId ? [expandedRunId] : [],
          onExpand: (expanded, record) => {
            setExpandedRunId(expanded ? record.id : null)
          },
        }}
      />
    </div>
  )
}
