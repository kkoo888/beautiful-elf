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
import {
  ClearOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  EyeOutlined,
  EyeInvisibleOutlined,
} from '@ant-design/icons'
import styles from './chat-panel.module.css'
import { SimpleMessageList } from './message-list'
import { MessageInput } from './message-input'
import { ApprovalDialog } from './approval-dialog'
import { ThinkingProcess } from './thinking-process'
import { ExecutionStatus } from './execution-status'
import type { UseChatReturn } from '../hooks/use-chat'

interface ChatContentProps {
  chat: UseChatReturn
  sidebarCollapsed?: boolean
  progressCollapsed?: boolean
  onToggleSidebar?: () => void
  onToggleProgress?: () => void
  hasProgressData?: boolean
}

export const ChatContent: React.FC<ChatContentProps> = ({
  chat,
  sidebarCollapsed,
  progressCollapsed,
  onToggleSidebar,
  onToggleProgress,
  hasProgressData,
}) => {
  const {
    messages,
    reasoningDepth,
    isLoading,
    chatStatus,
    selectedProviderId,
    selectedModelName,
    approvalRequest,
    thinkingSteps,
    isExecuting,
    currentStep,
    currentTool,
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
        <div className={styles.headerActions}>
          {onToggleSidebar && (
            <Tooltip title={sidebarCollapsed ? '展开侧栏' : '收起侧栏'}>
              <Button
                type="text"
                size="small"
                icon={sidebarCollapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
                onClick={onToggleSidebar}
              />
            </Tooltip>
          )}
          {onToggleProgress && (
            <Tooltip title={progressCollapsed ? '展开进展面板' : '收起进展面板'}>
              <Button
                type="text"
                size="small"
                icon={progressCollapsed ? <EyeOutlined /> : <EyeInvisibleOutlined />}
                onClick={onToggleProgress}
                style={{
                  color: hasProgressData && progressCollapsed
                    ? 'var(--color-primary, #ff8c42)'
                    : undefined,
                }}
              />
            </Tooltip>
          )}
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

      {/* 执行状态栏 */}
      <ExecutionStatus
        isExecuting={isExecuting}
        currentStep={currentStep}
        currentTool={currentTool}
      />

      {/* 思考过程 */}
      {thinkingSteps.length > 0 && (
        <ThinkingProcess
          steps={thinkingSteps}
          isThinking={isExecuting}
        />
      )}

      {/* 消息列表 */}
      <SimpleMessageList messages={messages} isLoading={isLoading} onFeedback={submitFeedback} />

      {/* 输入框 */}
      <MessageInput
        onSend={handleSend}
        disabled={isLoading}
        onStop={stopGeneration}
        isLoading={isLoading}
        chatStatus={chatStatus}
        providerId={selectedProviderId}
        modelName={selectedModelName}
        onModelChange={setModelSelection}
        reasoningDepth={reasoningDepth}
        onReasoningDepthChange={setReasoningDepth}
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
