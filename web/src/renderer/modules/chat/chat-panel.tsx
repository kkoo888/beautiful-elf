import { useState, useCallback, useEffect } from 'react'
import { ChatContent } from './components/chat-panel'
import { ConversationList } from './components/conversation-list'
import { ProgressTabs } from './components/progress-tabs'
import { useChat } from './hooks/use-chat'
import styles from './chat-sidebar.module.css'

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
            <ProgressTabs
              goalMode={goalMode}
              goalTasks={goalTasks}
              progressSteps={progressSteps}
              toolProgress={toolProgress}
              contextSources={contextSources}
              tokenStats={tokenStats}
            />
          )}
        </div>
      </div>
    </div>
  )
}
