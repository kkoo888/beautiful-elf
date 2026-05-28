/**
 * 反馈按钮组件
 * 👍👎 按钮 + 原因标签选择
 */

import React, { useCallback, useState } from 'react'
import styles from './chat-panel.module.css'
import type { FeedbackData, FeedbackReason, FeedbackType } from '../types/chat'

/** 反馈原因选项 */
const FEEDBACK_REASONS: { value: FeedbackReason; label: string }[] = [
  { value: 'inaccurate', label: '不准确' },
  { value: 'irrelevant', label: '不相关' },
  { value: 'harmful', label: '有害内容' },
  { value: 'outdated', label: '过时信息' },
  { value: 'unclear', label: '不够清晰' },
  { value: 'other', label: '其他' }
]

interface FeedbackButtonsProps {
  /** 消息 ID */
  messageId: string
  /** 已有的反馈数据 */
  feedback?: FeedbackData
  /** 提交反馈回调 */
  onSubmit: (data: FeedbackData) => Promise<void>
}

export const FeedbackButtons: React.FC<FeedbackButtonsProps> = ({
  messageId,
  feedback,
  onSubmit
}) => {
  const [selectedType, setSelectedType] = useState<FeedbackType | null>(
    feedback?.type ?? null
  )
  const [showReasons, setShowReasons] = useState(false)
  const [selectedReasons, setSelectedReasons] = useState<FeedbackReason[]>(
    feedback?.reasons ?? []
  )
  const [submitting, setSubmitting] = useState(false)

  const handleTypeClick = useCallback(
    async (type: FeedbackType) => {
      if (submitting) return

      // 如果点击已选中的类型，取消选择
      if (selectedType === type) {
        setSelectedType(null)
        setShowReasons(false)
        return
      }

      setSelectedType(type)

      if (type === 'negative') {
        setShowReasons(true)
      } else {
        // 👍 直接提交
        setShowReasons(false)
        setSubmitting(true)
        try {
          await onSubmit({ messageId, type })
        } finally {
          setSubmitting(false)
        }
      }
    },
    [messageId, selectedType, submitting, onSubmit]
  )

  const handleReasonToggle = useCallback((reason: FeedbackReason) => {
    setSelectedReasons((prev) =>
      prev.includes(reason) ? prev.filter((r) => r !== reason) : [...prev, reason]
    )
  }, [])

  const handleSubmitReasons = useCallback(async () => {
    if (submitting || selectedReasons.length === 0) return

    setSubmitting(true)
    try {
      await onSubmit({
        messageId,
        type: 'negative',
        reasons: selectedReasons
      })
      setShowReasons(false)
    } finally {
      setSubmitting(false)
    }
  }, [messageId, selectedReasons, submitting, onSubmit])

  return (
    <div>
      <div className={styles.feedbackContainer}>
        <button
          className={`${styles.feedbackButton} ${
            selectedType === 'positive' ? styles.feedbackButtonActive : ''
          }`}
          onClick={() => handleTypeClick('positive')}
          disabled={submitting}
          aria-label="有帮助"
          title="有帮助"
        >
          👍
        </button>
        <button
          className={`${styles.feedbackButton} ${
            selectedType === 'negative' ? styles.feedbackButtonActive : ''
          }`}
          onClick={() => handleTypeClick('negative')}
          disabled={submitting}
          aria-label="没帮助"
          title="没帮助"
        >
          👎
        </button>
      </div>

      {showReasons && (
        <div className={styles.feedbackReasons}>
          {FEEDBACK_REASONS.map(({ value, label }) => (
            <button
              key={value}
              className={`${styles.reasonTag} ${
                selectedReasons.includes(value) ? styles.reasonTagSelected : ''
              }`}
              onClick={() => handleReasonToggle(value)}
            >
              {label}
            </button>
          ))}
          <button
            className={styles.feedbackSubmit}
            onClick={handleSubmitReasons}
            disabled={selectedReasons.length === 0 || submitting}
            style={{
              marginLeft: 4,
              padding: '4px 12px',
              borderRadius: 12,
              border: 'none',
              background: selectedReasons.length > 0 ? '#ff8c42' : '#e8e8e8',
              color: selectedReasons.length > 0 ? '#fff' : '#999',
              fontSize: 12,
              cursor: selectedReasons.length > 0 ? 'pointer' : 'default'
            }}
          >
            提交
          </button>
        </div>
      )}
    </div>
  )
}
