/**
 * 消息气泡组件
 * 区分用户/AI 消息样式，AI 消息支持 Markdown 渲染和代码高亮
 */

import React, { useCallback, useEffect, useMemo, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import Prism from 'prismjs'
import 'prismjs/components/prism-typescript'
import 'prismjs/components/prism-javascript'
import 'prismjs/components/prism-python'
import 'prismjs/components/prism-json'
import 'prismjs/components/prism-bash'
import 'prismjs/components/prism-css'
import 'prismjs/components/prism-markdown'
import 'prismjs/components/prism-yaml'
import 'prismjs/components/prism-sql'
import 'prismjs/components/prism-rust'
import 'prismjs/components/prism-go'
import styles from './chat-panel.module.css'
import { FeedbackButtons } from './feedback-buttons'
import { QuickAnswerBadge } from './quick-answer-badge'
import type { ChatMessage, FeedbackData } from '../types/chat'

/** 格式化时间 */
const formatTime = (timestamp: number): string => {
  const date = new Date(timestamp)
  const hours = date.getHours().toString().padStart(2, '0')
  const minutes = date.getMinutes().toString().padStart(2, '0')
  return `${hours}:${minutes}`
}

/** 代码块组件 */
const CodeBlock: React.FC<{ className?: string; children: React.ReactNode }> = ({
  className,
  children,
}) => {
  const [copied, setCopied] = useState(false)
  const language = className?.replace('language-', '') ?? 'text'
  const code = String(children).replace(/\n$/, '')

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(code)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // fallback
      const textarea = document.createElement('textarea')
      textarea.value = code
      document.body.appendChild(textarea)
      textarea.select()
      document.execCommand('copy')
      document.body.removeChild(textarea)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }, [code])

  // 语法高亮
  const highlightedHtml = useMemo(() => {
    const grammar = Prism.languages[language] ?? Prism.languages.plaintext
    return Prism.highlight(code, grammar, language)
  }, [code, language])

  return (
    <div className={styles.codeBlock}>
      <div className={styles.codeHeader}>
        <span className={styles.codeLanguage}>{language}</span>
        <button className={styles.copyButton} onClick={handleCopy}>
          {copied ? '✓ 已复制' : '复制'}
        </button>
      </div>
      <pre className={styles.codeBody}>
        <code dangerouslySetInnerHTML={{ __html: highlightedHtml }} />
      </pre>
    </div>
  )
}

interface MessageBubbleProps {
  /** 消息数据 */
  message: ChatMessage
  /** 提交反馈回调 */
  onFeedback?: (data: FeedbackData) => Promise<void>
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({ message, onFeedback }) => {
  const isUser = message.role === 'user'
  const isAssistant = message.role === 'assistant'

  useEffect(() => {
    Prism.highlightAll()
  }, [message.content])

  return (
    <div
      className={`${styles.messageRow} ${
        isUser ? styles.messageRowUser : styles.messageRowAssistant
      }`}
    >
      <div className={`${styles.bubble} ${isUser ? styles.bubbleUser : styles.bubbleAssistant}`}>
        {isUser ? (
          <div className={styles.markdownContent}>
            {message.content.split('\n').map((line, i) => (
              <React.Fragment key={i}>
                {line}
                {i < message.content.split('\n').length - 1 && <br />}
              </React.Fragment>
            ))}
          </div>
        ) : (
          <div className={styles.markdownContent}>
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                code({ className, children, ...props }) {
                  const isInline = !className
                  if (isInline) {
                    return <code {...props}>{children}</code>
                  }
                  return <CodeBlock className={className}>{children}</CodeBlock>
                },
              }}
            >
              {message.content}
            </ReactMarkdown>
          </div>
        )}

        {/* 消息元数据 */}
        {(isAssistant || message.metadata) && (
          <div className={styles.messageMeta}>
            <span>{formatTime(message.createdAt)}</span>
            {message.metadata?.isCached && <QuickAnswerBadge visible />}
            {message.metadata?.intentRoute && (
              <span className={styles.intentBadge}>🧭 {message.metadata.intentRoute.module}</span>
            )}
          </div>
        )}

        {/* 用户消息时间 */}
        {isUser && (
          <div className={styles.messageMeta}>
            <span>{formatTime(message.createdAt)}</span>
          </div>
        )}

        {/* AI 反馈按钮 */}
        {isAssistant && onFeedback && (
          <FeedbackButtons
            messageId={message.id}
            feedback={message.feedback}
            onSubmit={onFeedback}
          />
        )}
      </div>
    </div>
  )
}
