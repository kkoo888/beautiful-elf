/**
 * 聊天主面板组件
 * 整合消息列表、输入框、推理深度切换、模型选择等
 */

import React, { useCallback, useEffect } from 'react'
import { Button, Tooltip } from 'antd'
import { ClearOutlined } from '@ant-design/icons'
import styles from './chat-panel.module.css'
import { SimpleMessageList } from './message-list'
import { MessageInput } from './message-input'
import { ReasoningDepthSwitch } from './reasoning-depth'
import { FullModelSelect } from '@/modules/shared/components/model-selector'
import { useChat } from '../hooks/use-chat'
import { useChatStore } from '@/stores/use-chat-store'
import { getEnabledProviders } from '@/modules/settings/services/settings-api'

export const ChatPanel: React.FC = () => {
  const {
    messages,
    reasoningDepth,
    isLoading,
    selectedProviderId,
    selectedModelName,
    sendMessage,
    setReasoningDepth,
    setModelSelection,
    submitFeedback,
    clearMessages,
    stopGeneration,
  } = useChat()

  const initDefaultModel = useChatStore((s) => s.initDefaultModel)

  // 首次加载：从接口取默认供应商和模型，写入 store
  useEffect(() => {
    void (async () => {
      try {
        const providers = await getEnabledProviders()
        initDefaultModel(providers)
      } catch { /* 忽略，用户可手动选择 */ }
    })()
  }, [initDefaultModel])

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
          <FullModelSelect
            providerId={selectedProviderId}
            modelName={selectedModelName}
            onChange={setModelSelection}
          />
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
      <SimpleMessageList messages={messages} isLoading={isLoading} onFeedback={submitFeedback} />

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
