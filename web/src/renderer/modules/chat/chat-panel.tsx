import { useState, useCallback, useEffect } from 'react'
import { Typography } from 'antd'
import { ThunderboltOutlined } from '@ant-design/icons'
import { ChatContent } from './components/chat-panel'
import { ConversationList } from './components/conversation-list'
import { AgentProgressIndicator } from './components/agent-progress'
import { ToolProgressIndicator } from './components/tool-progress'
import { ContextSourcesDisplay } from './components/context-sources'
import { TokenStatsBar } from './components/token-stats-bar'
import { GoalTaskBoard } from './components/goal-task-board'
import { useChat } from './hooks/use-chat'
import styles from './chat-sidebar.module.css'

const { Text } = Typography

/** 对话模块面板（含会话侧栏 + 右侧进展面板） */
export default function ChatPanel() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [progressCollapsed, setProgressCollapsed] = useState(true)  // 默认折叠，有数据时自动展开
  const chat = useChat()
  const {
    conversations,
    currentConversationId,
    createConversation,
    switchConversation,
    deleteConversation,
    toolProgress,
    contextSources,
    tokenStats,
    progressSteps,
    goalMode,
    goalTasks,
  } = chat

  const toggleSidebar = useCallback(() => {
    setSidebarCollapsed((prev) => !prev)
  }, [])

  const toggleProgress = useCallback(() => {
    setProgressCollapsed((prev) => !prev)
  }, [])

  const hasProgressData =
    toolProgress.length > 0 ||
    progressSteps.length > 0 ||
    contextSources.length > 0 ||
    tokenStats !== null ||
    goalMode

  // 有数据时自动展开进展面板
  useEffect(() => {
    if (hasProgressData && progressCollapsed) {
      setProgressCollapsed(false)
    }
  }, [hasProgressData])

  return (
    <div className={styles.layout}>
      <div className={styles.body}>
        {/* 会话侧栏 */}
        <div className={`${styles.sidebar} ${sidebarCollapsed ? styles.sidebarCollapsed : ''}`}>
          {!sidebarCollapsed && (
            <ConversationList
              conversations={conversations}
              currentId={currentConversationId}
              onCreate={createConversation}
              onSwitch={switchConversation}
              onDelete={deleteConversation}
            />
          )}
        </div>

        {/* 聊天内容区 */}
        <div className={styles.content}>
          <ChatContent
            chat={chat}
            sidebarCollapsed={sidebarCollapsed}
            progressCollapsed={progressCollapsed}
            onToggleSidebar={toggleSidebar}
            onToggleProgress={toggleProgress}
            hasProgressData={hasProgressData}
          />
        </div>

        {/* 右侧进展面板 */}
        <div
          className={`${styles.progressPanel} ${progressCollapsed ? styles.progressPanelCollapsed : ''}`}
        >
          {!progressCollapsed && (
            <div className={styles.progressPanelInner}>
              {/* Goal 模式任务看板 — Goal 模式激活时立即显示 */}
              {goalMode && (
                <GoalTaskBoard
                  tasks={goalTasks}
                  iterations={progressSteps.find((s) => s.step === 'goal_progress')?.['iterations'] as number || 0}
                  maxIterations={5}
                  tokensUsed={tokenStats ? tokenStats.promptTokens + tokenStats.completionTokens : 0}
                  tokenBudget={50000}
                />
              )}

              <h4 className={styles.progressPanelTitle}>
                <ThunderboltOutlined /> 执行进展
              </h4>

              {/* Agent 执行进展 */}
              {progressSteps.length > 0 && (
                <div className={styles.progressSection}>
                  <div className={styles.progressSectionTitle}>Agent 步骤</div>
                  <AgentProgressIndicator steps={progressSteps} />
                </div>
              )}

              {/* 工具执行进度 */}
              {toolProgress.length > 0 && (
                <div className={styles.progressSection}>
                  <div className={styles.progressSectionTitle}>工具调用</div>
                  <ToolProgressIndicator tools={toolProgress} />
                </div>
              )}

              {/* 上下文引用来源 */}
              {contextSources.length > 0 && (
                <div className={styles.progressSection}>
                  <div className={styles.progressSectionTitle}>参考来源</div>
                  <ContextSourcesDisplay sources={contextSources} />
                </div>
              )}

              {/* Token 统计 */}
              {tokenStats && (
                <div className={styles.progressSection}>
                  <div className={styles.progressSectionTitle}>Token 消耗</div>
                  <TokenStatsBar
                    promptTokens={tokenStats.promptTokens}
                    completionTokens={tokenStats.completionTokens}
                  />
                </div>
              )}

              {/* 无数据时展示空状态 */}
              {!hasProgressData && (
                <div className={styles.progressEmpty}>
                  <span className={styles.progressEmptyIcon}>🔍</span>
                  <Text className={styles.progressEmptyText} type="secondary">
                    发送消息后，这里将展示 Agent 的执行进展
                  </Text>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
