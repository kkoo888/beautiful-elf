/**
 * 消息输入框组件
 * 多行输入，Enter 发送，Shift+Enter 换行
 */

import React, { useCallback, useRef, useState } from 'react'
import styles from './chat-panel.module.css'

interface MessageInputProps {
  /** 发送消息回调 */
  onSend: (content: string) => void
  /** 是否禁用（正在生成中） */
  disabled?: boolean
  /** 停止生成回调 */
  onStop?: () => void
  /** 是否正在加载 */
  isLoading?: boolean
}

export const MessageInput: React.FC<MessageInputProps> = ({
  onSend,
  disabled = false,
  onStop,
  isLoading = false
}) => {
  const [value, setValue] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  /** 自动调整高度 */
  const adjustHeight = useCallback(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 120)}px`
  }, [])

  /** 发送消息 */
  const handleSend = useCallback(() => {
    const trimmed = value.trim()
    if (!trimmed || disabled) return

    onSend(trimmed)
    setValue('')

    // 重置高度
    requestAnimationFrame(() => {
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto'
      }
    })
  }, [value, disabled, onSend])

  /** 键盘事件 */
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        handleSend()
      }
    },
    [handleSend]
  )

  /** 输入变化 */
  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      setValue(e.target.value)
      adjustHeight()
    },
    [adjustHeight]
  )

  return (
    <div className={styles.inputContainer}>
      <div className={styles.inputWrapper}>
        <textarea
          ref={textareaRef}
          className={styles.inputTextarea}
          value={value}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder="输入消息... (Enter 发送，Shift+Enter 换行)"
          disabled={disabled}
          rows={1}
          aria-label="消息输入框"
        />
        {isLoading && onStop ? (
          <button
            className={styles.stopButton}
            onClick={onStop}
            aria-label="停止生成"
            title="停止生成"
          >
            ■
          </button>
        ) : (
          <button
            className={styles.sendButton}
            onClick={handleSend}
            disabled={!value.trim() || disabled}
            aria-label="发送消息"
            title="发送消息"
          >
            ➤
          </button>
        )}
      </div>
      <div className={styles.inputHint}>
        <div className={styles.shortcutHint}>
          <span className={styles.shortcutKey}>Enter</span>
          <span>发送</span>
          <span className={styles.shortcutKey}>Shift</span>
          <span>+</span>
          <span className={styles.shortcutKey}>Enter</span>
          <span>换行</span>
        </div>
      </div>
    </div>
  )
}
