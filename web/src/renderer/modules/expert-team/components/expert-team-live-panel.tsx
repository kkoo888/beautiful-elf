/**
 * 专家团实时执行面板
 *
 * 展示专家团执行过程中的实时状态：
 * - 专家状态卡片（谁在工作、谁完成了）
 * - 思考链/推理过程展示
 * - 任务进度
 *
 * 数据来源：父组件通过 props 传入（SSE 流式事件驱动）
 */

import { Card, Tag, Space, Typography, Progress, Empty, Collapse } from 'antd'
import {
  LoadingOutlined,
  CheckCircleFilled,
  CloseCircleFilled,
  BulbOutlined,
} from '@ant-design/icons'
import { useMemo } from 'react'
import { ExpertAvatar } from '@/components/expert-avatar'

const { Text, Paragraph } = Typography

interface LiveExpert {
  name: string
  role: string
  avatar: string
  status: string
  thinking: string
  durationMs: number
}

interface ExpertTeamLivePanelProps {
  /** 当前选中的专家团 ID */
  teamId?: number
  /** 最大轮次 */
  maxRounds?: number
  /** 专家实时状态（SSE 驱动） */
  experts: Map<string, LiveExpert>
  /** 整体执行状态 */
  status: string
  /** 最终输出 */
  output?: string
}

/** 专家角色颜色映射 */
const ROLE_COLORS: Record<string, string> = {
  Orchestrator: '#1890ff',
  Synthesizer: '#722ed1',
  '架构师': '#1890ff',
  '测试专家': '#52c41a',
  '产品经理': '#faad14',
  '设计师': '#eb2f96',
  '安全专家': '#f5222d',
  '创意总监': '#1890ff',
  '创意策划师': '#faad14',
  '图文创作专家': '#52c41a',
}

function getRoleColor(role: string): string {
  return ROLE_COLORS[role] || '#8c8c8c'
}

/** 专家状态卡片 */
function ExpertCard({ expert }: { expert: LiveExpert }) {
  const statusIcon: Record<string, React.ReactNode> = {
    idle: <span style={{ color: '#8c8c8c', fontSize: 12 }}>⏰</span>,
    running: <LoadingOutlined style={{ color: '#1890ff' }} />,
    done: <CheckCircleFilled style={{ color: '#52c41a' }} />,
    failed: <CloseCircleFilled style={{ color: '#f5222d' }} />,
  }

  const statusLabel: Record<string, string> = {
    idle: '待命',
    running: '分析中...',
    done: '已完成',
    failed: '失败',
  }

  const statusColor: Record<string, string> = {
    idle: 'default',
    running: 'processing',
    done: 'success',
    failed: 'error',
  }

  return (
    <Card
      size="small"
      style={{
        borderLeft: `3px solid ${getRoleColor(expert.role)}`,
        opacity: expert.status === 'idle' ? 0.5 : 1,
      }}
      styles={{ body: { padding: '8px 12px' } }}
    >
      <Space direction="vertical" size={4} style={{ width: '100%' }}>
        <Space>
          <ExpertAvatar avatar={expert.avatar} size={28} bgColor={getRoleColor(expert.role)} color="#fff" />
          <Text strong>{expert.name}</Text>
          <Tag color={getRoleColor(expert.role)} style={{ margin: 0 }}>
            {expert.role}
          </Tag>
          <Tag color={statusColor[expert.status]} icon={statusIcon[expert.status]} style={{ margin: 0 }}>
            {statusLabel[expert.status]}
          </Tag>
        </Space>
        {expert.status === 'running' && expert.thinking && (
          <Text
            type="secondary"
            style={{ fontSize: 12, lineHeight: '16px' }}
            ellipsis={{ tooltip: true }}
          >
            {expert.thinking.slice(0, 80)}...
          </Text>
        )}
        {expert.status === 'done' && expert.durationMs > 0 && (
          <Text type="secondary" style={{ fontSize: 12 }}>
            耗时 {(expert.durationMs / 1000).toFixed(1)}s
          </Text>
        )}
      </Space>
    </Card>
  )
}

/** 主面板 */
export function ExpertTeamLivePanel({
  teamId,
  maxRounds = 3,
  experts,
  status,
  output,
}: ExpertTeamLivePanelProps) {
  // 计算进度百分比
  const progressPercent = useMemo(() => {
    if (status === 'completed') return 100
    if (status === 'idle') return 0
    if (status === 'running' || status === 'orchestrating') return 5
    if (status === 'synthesizing') return 90
    if (status === 'discussing') return 10 + (experts.size / Math.max(maxRounds, 1)) * 80
    return 0
  }, [status, experts.size, maxRounds])

  const statusLabel: Record<string, string> = {
    idle: '等待执行',
    running: '🎯 正在启动...',
    orchestrating: '🎯 编排器分析任务...',
    discussing: '💬 专家讨论中',
    synthesizing: '📋 汇总器生成报告...',
    completed: '✅ 执行完成',
    failed: '❌ 执行失败',
  }

  if (status === 'idle' && experts.size === 0) {
    return (
      <Card title="📡 实时执行状态" size="small">
        <Empty
          description="执行专家团后，这里会实时显示专家工作状态和推理过程"
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        />
      </Card>
    )
  }

  // 收集所有思考记录
  const thinkingExperts = Array.from(experts.values()).filter((e) => e.thinking)

  return (
    <Card
      title={
        <Space>
          <span>📡 实时执行状态</span>
          {teamId && <Tag>Team #{teamId}</Tag>}
        </Space>
      }
      size="small"
      extra={
        <Tag
          color={
            status === 'completed'
              ? 'success'
              : status === 'failed'
                ? 'error'
                : 'processing'
          }
        >
          {statusLabel[status] || status}
        </Tag>
      }
    >
      {/* 进度条 */}
      <Progress
        percent={progressPercent}
        status={
          status === 'completed'
            ? 'success'
            : status === 'failed'
              ? 'exception'
              : 'active'
        }
        showInfo={false}
        style={{ marginBottom: 16 }}
      />

      {/* 专家状态卡片 */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))',
          gap: 8,
          marginBottom: 16,
        }}
      >
        {Array.from(experts.values()).map((expert) => (
          <ExpertCard key={`${expert.name}-${expert.role}`} expert={expert} />
        ))}
      </div>

      {/* 思考链/推理过程 */}
      {thinkingExperts.length > 0 && (
        <Collapse
          size="small"
          defaultActiveKey={['thinking']}
          items={[
            {
              key: 'thinking',
              label: (
                <Space>
                  <BulbOutlined />
                  <span>推理过程</span>
                  <Tag>{thinkingExperts.length} 条记录</Tag>
                </Space>
              ),
              children: (
                <div style={{ maxHeight: 300, overflow: 'auto' }}>
                  {thinkingExperts.map((expert) => (
                    <div key={`${expert.name}-${expert.role}`} style={{ marginBottom: 12 }}>
                      <Space>
                        <ExpertAvatar avatar={expert.avatar} size={24} bgColor={getRoleColor(expert.role)} color="#fff" />
                        <Text strong>{expert.name}</Text>
                        <Tag color={getRoleColor(expert.role)} style={{ margin: 0 }}>
                          {expert.role}
                        </Tag>
                        {expert.durationMs > 0 && (
                          <Text type="secondary" style={{ fontSize: 12 }}>
                            {(expert.durationMs / 1000).toFixed(1)}s
                          </Text>
                        )}
                      </Space>
                      <Paragraph
                        style={{
                          marginTop: 4,
                          whiteSpace: 'pre-wrap',
                          maxHeight: 200,
                          overflow: 'auto',
                          fontSize: 13,
                        }}
                      >
                        {expert.thinking}
                      </Paragraph>
                    </div>
                  ))}
                </div>
              ),
            },
          ]}
        />
      )}

      {/* 最终输出 */}
      {status === 'completed' && output && (
        <Card size="small" title="📋 最终报告" style={{ marginTop: 16 }}>
          <Paragraph style={{ whiteSpace: 'pre-wrap', maxHeight: 400, overflow: 'auto' }}>
            {output}
          </Paragraph>
        </Card>
      )}
    </Card>
  )
}
