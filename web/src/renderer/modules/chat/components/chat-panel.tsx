/**
 * 聊天主面板组件
 * 整合消息列表、输入框、推理深度切换等
 */

import React, { useCallback } from 'react'
import { Button, Tooltip } from 'antd'
import { ClearOutlined, ReloadOutlined } from '@ant-design/icons'
import styles from './chat-panel.module.css'
import { SimpleMessageList } from './message-list'
import { MessageInput } from './message-input'
import { ReasoningDepthSwitch } from './reasoning-depth'
import { useChat } from '../hooks/use-chat'

export const ChatPanel: React.FC = () => {
  const {
    messages,
    reasoningDepth,
    isLoading,
    sendMessage,
    setReasoningDepth,
    submitFeedback,
    clearMessages,
    stopGeneration
  } = useChat()

  const handleSend = useCallback(
    (content: string) => {
      sendMessage(content)
    },
    [sendMessage]
  )

  const handleClear = useCallback(() => {
    clearMessages()
  }, [clearMessages])

  return (
    <div className={styles.chatPanel}>
      {/* 顶部操作栏 */}
      <div className={styles.chatHeader}>
        <h4 className={styles.chatTitle}>💬 对话</h4>
        <div className={styles.headerActions}>
          <ReasoningDepthSwitch value={reasoningDepth} onChange={setReasoningDepth} />
          <Tooltip title="清空对话">
            <Button
              type="text"
              size="small"
              icon={<ClearOutlined />}
              onClick={handleClear}
              disabled={messages.length === 0}
            />
          </Tooltip>
        </div>
      </div>

      {/* 消息列表 */}
      <SimpleMessageList
        messages={messages}
        isLoading={isLoading}
        onFeedback={submitFeedback}
      />

      {/* 输入框 */}
      <MessageInput
        onSend={handleSend}
        disabled={isLoading}
        onStop={stopGeneration}
        isLoading={isLoading}
      />
    </div>
  )
}
