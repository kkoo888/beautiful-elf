/**
 * 聊天主面板组件（v4.2 — 进展信息移至右侧面板）
 * 整合消息列表、输入框、推理深度切换、模型选择等
 *
 * 注意：useChat 由父组件 ChatPanel 调用，本组件通过 props 接收，
 * 避免重复调用导致 effect 重复触发。
 * 进展类信息（Agent 进展、工具进度、上下文引用、token 统计）
 * 由父组件统一在右侧面板展示。
 */

import React, { useCallback } from 'react'
import { Button, Tooltip } from 'antd'
import { ClearOutlined } from '@ant-design/icons'
import styles from './chat-panel.module.css'
import { SimpleMessageList } from './message-list'
import { MessageInput } from './message-input'
import { ReasoningDepthSwitch } from './reasoning-depth'
import { FullModelSelect } from '@/modules/shared/components/model-selector'
import { ApprovalDialog } from './approval-dialog'
import type { UseChatReturn } from '../hooks/use-chat'

interface ChatContentProps {
  chat: UseChatReturn
}

export const ChatContent: React.FC<ChatContentProps> = ({ chat }) => {
  const {
    messages,
    reasoningDepth,
    isLoading,
    selectedProviderId,
    selectedModelName,
    approvalRequest,
    sendMessage,
    setReasoningDepth,
    setModelSelection,
    submitFeedback,
    clearMessages,
    stopGeneration,
    respondApproval,
  } = chat

  const handleSend = useCallback(
    (content: string, options?: { expertTeamId?: number; skillId?: number; teamMode?: 'off' | 'auto' | 'manual'; goalMode?: boolean }) => {
      sendMessage(content, options)
    },
    [sendMessage],
  )

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
              onClick={clearMessages}
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

      {/* 审批对话框 */}
      <ApprovalDialog
        request={approvalRequest}
        visible={!!approvalRequest}
        onApprove={() => respondApproval(true)}
        onReject={() => respondApproval(false)}
      />
    </div>
  )
}
