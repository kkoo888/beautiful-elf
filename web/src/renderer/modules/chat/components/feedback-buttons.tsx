/**
 * 反馈按钮组件（使用 Ant Design）
 * 👍👎 按钮，点击👎弹出反馈弹窗
 */

import React, { useCallback, useState } from 'react'
import { Button, Tooltip } from 'antd'
import { LikeOutlined, DislikeOutlined, LikeFilled, DislikeFilled } from '@ant-design/icons'
import { FeedbackModal } from './feedback-modal'
import type { FeedbackData, FeedbackType } from '../types/chat'

export interface FeedbackButtonsProps {
  /** 消息 ID */
  messageId: string
  /** 已有的反馈数据 */
  feedback?: FeedbackData
  /** 提交反馈回调 */
  onFeedback: (data: FeedbackData) => Promise<void>
}

export const FeedbackButtons: React.FC<FeedbackButtonsProps> = ({
  messageId,
  feedback,
  onFeedback,
}) => {
  const [selectedType, setSelectedType] = useState<FeedbackType | null>(feedback?.type ?? null)
  const [modalVisible, setModalVisible] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  /** 点击 👍 直接提交 */
  const handlePositive = useCallback(async () => {
    if (submitting) return

    // 取消已选中的👍
    if (selectedType === 'positive') {
      setSelectedType(null)
      return
    }

    setSubmitting(true)
    try {
      await onFeedback({ messageId, type: 'positive' })
      setSelectedType('positive')
    } finally {
      setSubmitting(false)
    }
  }, [messageId, selectedType, submitting, onFeedback])

  /** 点击 👎 弹出反馈弹窗 */
  const handleNegative = useCallback(() => {
    if (submitting) return

    // 取消已选中的👎
    if (selectedType === 'negative') {
      setSelectedType(null)
      return
    }

    setModalVisible(true)
  }, [selectedType, submitting])

  /** 提交负面反馈 */
  const handleModalSubmit = useCallback(
    async (data: FeedbackData) => {
      setSubmitting(true)
      try {
        await onFeedback(data)
        setSelectedType('negative')
        setModalVisible(false)
      } finally {
        setSubmitting(false)
      }
    },
    [onFeedback]
  )

  return (
    <>
      <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginTop: 6 }}>
        <Tooltip title="有帮助">
          <Button
            type="text"
            size="small"
            icon={selectedType === 'positive' ? <LikeFilled /> : <LikeOutlined />}
            onClick={handlePositive}
            loading={submitting && selectedType !== 'negative'}
            style={{
              color: selectedType === 'positive' ? 'var(--ant-color-primary)' : undefined,
            }}
          />
        </Tooltip>
        <Tooltip title="没帮助">
          <Button
            type="text"
            size="small"
            icon={selectedType === 'negative' ? <DislikeFilled /> : <DislikeOutlined />}
            onClick={handleNegative}
            loading={submitting && selectedType === 'negative'}
            style={{
              color: selectedType === 'negative' ? 'var(--ant-color-error)' : undefined,
            }}
          />
        </Tooltip>
      </div>

      <FeedbackModal
        visible={modalVisible}
        messageId={messageId}
        onClose={() => setModalVisible(false)}
        onSubmit={handleModalSubmit}
        loading={submitting}
      />
    </>
  )
}
