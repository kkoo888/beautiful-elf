/** 运行监控组件（Timeline） */

import { Timeline, Tag, Typography, Spin, Empty } from 'antd'
import { CheckCircleFilled, CloseCircleFilled, LoadingOutlined, ClockCircleOutlined, MinusCircleFilled } from '@ant-design/icons'
import { useState } from 'react'
import type { WorkflowRun, NodeRun, NodeStatus } from '../types/workflow'
import styles from './workflow-panel.module.css'

const { Text } = Typography

const NODE_STATUS_ICON: Record<NodeStatus, React.ReactNode> = {
  success: <CheckCircleFilled style={{ color: 'var(--ant-color-success)' }} />,
  failed: <CloseCircleFilled style={{ color: 'var(--ant-color-error)' }} />,
  running: <LoadingOutlined style={{ color: 'var(--ant-color-primary)' }} />,
  pending: <ClockCircleOutlined style={{ color: 'var(--ant-color-text-quaternary)' }} />,
  skipped: <MinusCircleFilled style={{ color: 'var(--ant-color-text-quaternary)' }} />,
}

const NODE_STATUS_COLOR: Record<NodeStatus, string> = {
  success: 'green',
  failed: 'red',
  running: 'blue',
  pending: 'gray',
  skipped: 'gray',
}

function formatDuration(ms?: number): string {
  if (ms === undefined || ms === null) return ''
  if (ms < 1000) return `${ms}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
  return `${Math.floor(ms / 60000)}m ${Math.round((ms % 60000) / 1000)}s`
}

interface WorkflowMonitorProps {
  runs: WorkflowRun[]
  loading?: boolean
}

export function WorkflowMonitor({ runs, loading }: WorkflowMonitorProps) {
  const [selectedRunId, setSelectedRunId] = useState<string | null>(runs[0]?.id ?? null)

  if (loading) {
    return <Spin style={{ display: 'block', textAlign: 'center', padding: 48 }} />
  }

  if (runs.length === 0) {
    return <Empty description="暂无运行记录" />
  }

  const selectedRun = runs.find((r) => r.id === selectedRunId) ?? runs[0]

  return (
    <div className={styles.monitorContainer}>
      <div className={styles.runList}>
        {runs.map((run) => (
          <div
            key={run.id}
            className={`${styles.runCard} ${run.id === selectedRun.id ? styles.runCardActive : ''}`}
            onClick={() => setSelectedRunId(run.id)}
          >
            <div className={styles.runName}>{run.workflowName}</div>
            <div className={styles.runMeta}>
              <Tag color={run.status === 'success' ? 'success' : run.status === 'failed' ? 'error' : run.status === 'running' ? 'processing' : 'default'}>
                {run.status === 'success' ? '成功' : run.status === 'failed' ? '失败' : run.status === 'running' ? '运行中' : '已取消'}
              </Tag>
              {run.duration && <span>{formatDuration(run.duration)}</span>}
            </div>
          </div>
        ))}
      </div>
      <div className={styles.timelineContainer}>
        <Text strong style={{ display: 'block', marginBottom: 16 }}>
          {selectedRun.workflowName} - 执行详情
        </Text>
        <Timeline
          items={selectedRun.nodeRuns.map((node: NodeRun) => ({
            dot: NODE_STATUS_ICON[node.status],
            color: NODE_STATUS_COLOR[node.status],
            children: (
              <div>
                <Text strong>{node.nodeName}</Text>
                <Tag color={NODE_STATUS_COLOR[node.status]} style={{ marginLeft: 8 }}>
                  {node.status === 'success' ? '成功' : node.status === 'failed' ? '失败' : node.status === 'running' ? '运行中' : node.status === 'skipped' ? '已跳过' : '等待中'}
                </Tag>
                {node.duration !== undefined && (
                  <span className={styles.nodeDuration}>{formatDuration(node.duration)}</span>
                )}
                {node.error && (
                  <div>
                    <Text type="danger" style={{ fontSize: 12 }}>{node.error}</Text>
                  </div>
                )}
              </div>
            ),
          }))}
        />
      </div>
    </div>
  )
}
