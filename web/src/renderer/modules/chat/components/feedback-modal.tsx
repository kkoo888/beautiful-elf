/**
 * 反馈弹窗组件
 * 使用 Ant Design Modal + Checkbox.Group + TextArea
 */

import React, { useCallback, useState } from 'react'
import { Modal, Checkbox, Input, Space, Typography } from 'antd'
import type { FeedbackData, FeedbackReason } from '../types/chat'

const { Text } = Typography
const { TextArea } = Input

/** 反馈原因选项 */
const REASON_OPTIONS: { value: FeedbackReason; label: string }[] = [
  { value: 'inaccurate', label: '不准确' },
  { value: 'irrelevant', label: '不相关' },
  { value: 'harmful', label: '有害' },
  { value: 'outdated', label: '过时' },
  { value: 'unclear', label: '不够清晰' },
  { value: 'other', label: '其他' },
]

export interface FeedbackModalProps {
  /** 是否可见 */
  visible: boolean
  /** 消息 ID */
  messageId: string
  /** 关闭回调 */
  onClose: () => void
  /** 提交回调 */
  onSubmit: (data: FeedbackData) => Promise<void>
  /** 提交中 */
  loading?: boolean
}

export const FeedbackModal: React.FC<FeedbackModalProps> = ({
  visible,
  messageId,
  onClose,
  onSubmit,
  loading = false,
}) => {
  const [selectedReasons, setSelectedReasons] = useState<FeedbackReason[]>([])
  const [comment, setComment] = useState('')

  const handleReset = useCallback(() => {
    setSelectedReasons([])
    setComment('')
  }, [])

  const handleClose = useCallback(() => {
    handleReset()
    onClose()
  }, [handleReset, onClose])

  const handleSubmit = useCallback(async () => {
    await onSubmit({
      messageId,
      type: 'negative',
      reasons: selectedReasons.length > 0 ? selectedReasons : undefined,
      comment: comment.trim() || undefined,
    })
    handleReset()
  }, [messageId, selectedReasons, comment, onSubmit, handleReset])

  return (
    <Modal
      title="👎 反馈详情"
      open={visible}
      onCancel={handleClose}
      onOk={handleSubmit}
      okText="提交反馈"
      cancelText="取消"
      confirmLoading={loading}
      okButtonProps={{ disabled: selectedReasons.length === 0 && !comment.trim() }}
      destroyOnClose
      width={420}
    >
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        <div>
          <Text strong style={{ display: 'block', marginBottom: 8 }}>
            请选择反馈原因（可多选）：
          </Text>
          <Checkbox.Group
            options={REASON_OPTIONS.map((opt) => ({
              label: opt.label,
              value: opt.value,
            }))}
            value={selectedReasons}
            onChange={(values) => setSelectedReasons(values as FeedbackReason[])}
            style={{ display: 'flex', flexWrap: 'wrap', gap: '8px 16px' }}
          />
        </div>

        <div>
          <Text strong style={{ display: 'block', marginBottom: 8 }}>
            补充说明（可选）：
          </Text>
          <TextArea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="请描述具体问题，帮助我们改进..."
            rows={3}
            maxLength={500}
            showCount
          />
        </div>
      </Space>
    </Modal>
  )
}
