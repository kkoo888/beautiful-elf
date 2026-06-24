import { useState } from 'react'
import { Typography, Badge } from 'antd'
import {
  ThunderboltOutlined,
  LinkOutlined,
  DashboardOutlined,
  BarChartOutlined,
} from '@ant-design/icons'
import { AgentProgressIndicator } from './agent-progress'
import { ToolProgressIndicator } from './tool-progress'
import { ContextSourcesDisplay } from './context-sources'
import { TokenStatsBar } from './token-stats-bar'
import { GoalTaskBoard } from './goal-task-board'
import type { ProgressStep, ToolProgress, ContextSource, GoalTask } from '../types/chat'

const { Text } = Typography

interface ProgressTabsProps {
  goalMode: boolean
  goalTasks: GoalTask[]
  progressSteps: ProgressStep[]
  toolProgress: ToolProgress[]
  contextSources: ContextSource[]
  tokenStats: { promptTokens: number; completionTokens: number } | null
  maxIterations?: number
  tokenBudget?: number
}

type TabKey = 'progress' | 'references' | 'board' | 'stats'

export function ProgressTabs({
  goalMode,
  goalTasks,
  progressSteps,
  toolProgress,
  contextSources,
  tokenStats,
  maxIterations = 50,
  tokenBudget = 50000,
}: ProgressTabsProps) {
  const [activeTab, setActiveTab] = useState<TabKey>('progress')

  const tabs = [
    {
      key: 'progress' as TabKey,
      label: '进展',
      icon: <ThunderboltOutlined />,
      count: progressSteps.length + toolProgress.length,
    },
    {
      key: 'references' as TabKey,
      label: '引用',
      icon: <LinkOutlined />,
      count: contextSources.length,
    },
    ...(goalMode
      ? [
          {
            key: 'board' as TabKey,
            label: '看板',
            icon: <DashboardOutlined />,
            count: goalTasks.length,
          },
        ]
      : []),
    {
      key: 'stats' as TabKey,
      label: '统计',
      icon: <BarChartOutlined />,
      count: tokenStats ? 1 : 0,
    },
  ]

  const renderContent = () => {
    switch (activeTab) {
      case 'progress':
        return (
          <div style={{ flex: 1, overflowY: 'auto', padding: 12 }}>
            {progressSteps.length > 0 && (
              <div style={{ marginBottom: 16 }}>
                <AgentProgressIndicator steps={progressSteps} />
              </div>
            )}
            {toolProgress.length > 0 && (
              <div style={{ marginBottom: 16 }}>
                <div style={{ fontSize: 12, fontWeight: 500, color: '#888', marginBottom: 8, textTransform: 'uppercase', letterSpacing: 0.5 }}>
                  工具调用
                </div>
                <ToolProgressIndicator tools={toolProgress} />
              </div>
            )}
            {progressSteps.length === 0 && toolProgress.length === 0 && (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '40px 20px', color: '#bbb', textAlign: 'center', gap: 8 }}>
                <ThunderboltOutlined style={{ fontSize: 28, opacity: 0.4 }} />
                <Text type="secondary" style={{ fontSize: 12 }}>发送消息后展示执行进展</Text>
              </div>
            )}
          </div>
        )

      case 'references':
        return (
          <div style={{ flex: 1, overflowY: 'auto', padding: 12 }}>
            {contextSources.length > 0 ? (
              <ContextSourcesDisplay sources={contextSources} />
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '40px 20px', color: '#bbb', textAlign: 'center', gap: 8 }}>
                <LinkOutlined style={{ fontSize: 28, opacity: 0.4 }} />
                <Text type="secondary" style={{ fontSize: 12 }}>暂无参考来源</Text>
              </div>
            )}
          </div>
        )

      case 'board':
        return (
          <div style={{ flex: 1, overflowY: 'auto', padding: 12 }}>
            <GoalTaskBoard
              tasks={goalTasks}
              iterations={
                progressSteps.find((s) => s.step === 'goal_progress')?.[
                  'iterations'
                ] as number || 0
              }
              maxIterations={maxIterations}
              tokensUsed={
                tokenStats
                  ? tokenStats.promptTokens + tokenStats.completionTokens
                  : 0
              }
              tokenBudget={tokenBudget}
            />
          </div>
        )

      case 'stats':
        return (
          <div style={{ flex: 1, overflowY: 'auto', padding: 12 }}>
            {tokenStats ? (
              <TokenStatsBar
                promptTokens={tokenStats.promptTokens}
                completionTokens={tokenStats.completionTokens}
              />
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '40px 20px', color: '#bbb', textAlign: 'center', gap: 8 }}>
                <BarChartOutlined style={{ fontSize: 28, opacity: 0.4 }} />
                <Text type="secondary" style={{ fontSize: 12 }}>暂无统计数据</Text>
              </div>
            )}
          </div>
        )
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Tab 导航 */}
      <div style={{ display: 'flex', borderBottom: '1px solid #f0f0f0', padding: '0 8px', gap: 2, flexShrink: 0 }}>
        {tabs.map((tab) => (
          <button
            key={tab.key}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 4,
              padding: '8px 10px',
              border: 'none',
              background: 'transparent',
              cursor: 'pointer',
              borderBottom: activeTab === tab.key ? '2px solid #1677ff' : '2px solid transparent',
              color: activeTab === tab.key ? '#1677ff' : '#888',
              fontSize: 12,
              fontWeight: activeTab === tab.key ? 500 : 400,
              transition: 'all 0.2s',
            }}
            onClick={() => setActiveTab(tab.key)}
          >
            <span style={{ fontSize: 13 }}>{tab.icon}</span>
            <span style={{ fontSize: 12 }}>{tab.label}</span>
            {tab.count > 0 && (
              <Badge
                count={tab.count}
                size="small"
                overflowCount={99}
                style={{ marginLeft: 2 }}
              />
            )}
          </button>
        ))}
      </div>

      {/* Tab 内容 */}
      {renderContent()}
    </div>
  )
}
