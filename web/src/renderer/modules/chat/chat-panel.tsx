import { useState, useCallback } from 'react'
import { Button, Tooltip } from 'antd'
import { MenuFoldOutlined, MenuUnfoldOutlined } from '@ant-design/icons'
import { PageHeader } from '@/components/page-header'
import { ChatContent } from './components/chat-panel'
import { ConversationList } from './components/conversation-list'
import { useChat } from './hooks/use-chat'
import styles from './chat-sidebar.module.css'

/** 对话模块面板（含会话侧栏） */
export default function ChatPanel() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const chat = useChat()
  const {
    conversations,
    currentConversationId,
    createConversation,
    switchConversation,
    deleteConversation,
  } = chat

  const toggleSidebar = useCallback(() => {
    setSidebarCollapsed((prev) => !prev)
  }, [])

  return (
    <div className={styles.layout}>
      <PageHeader
        title="💬 对话"
        description="与 AI 助手对话"
        extra={
          <Tooltip title={sidebarCollapsed ? '展开侧栏' : '收起侧栏'}>
            <Button
              type="text"
              icon={sidebarCollapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
              onClick={toggleSidebar}
            />
          </Tooltip>
        }
      />
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
          <ChatContent chat={chat} />
        </div>
      </div>
    </div>
  )
}
