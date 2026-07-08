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
import {
  CheckCircleOutlined,
  ExperimentOutlined,
  BarChartOutlined,
  FileTextOutlined,
  BulbOutlined,
  CaretRightOutlined,
} from '@ant-design/icons'
import 'prismjs/components/prism-yaml'
import 'prismjs/components/prism-sql'
import 'prismjs/components/prism-rust'
import 'prismjs/components/prism-go'
import styles from './chat-panel.module.css'
import { FeedbackButtons } from './feedback-buttons'
import { QuickAnswerBadge } from './quick-answer-badge'
import { IntentCorrectionButton } from './intent-correction-button'
import type { ChatMessage, FeedbackData } from '../types/chat'

/** ◆ 符号替换为前端 UI icon */
function renderIconMarkers(children: React.ReactNode): React.ReactNode {
  return React.Children.map(children, (child) => {
    if (typeof child !== 'string') return child
    const parts = child.split('◆')
    if (parts.length <= 1) return child
    return parts.flatMap((part, i) => {
      if (i === 0) return [part]
      // 根据上下文选择 icon
      const nextText = parts[i] || ''
      let Icon = BulbOutlined
      if (nextText.includes('分析完成')) Icon = ExperimentOutlined
      else if (nextText.includes('评估')) Icon = BarChartOutlined
      else if (nextText.includes('最终报告')) Icon = FileTextOutlined
      else if (nextText.includes('完成')) Icon = CheckCircleOutlined
      return [
        <Icon key={`icon-${i}`} style={{ color: '#1890ff', marginRight: 4, fontSize: 14 }} />,
        part,
      ]
    })
  })
}

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

/** 可折叠思考块 */
function ThinkingBlock({ thinking }: { thinking: string }) {
  const [expanded, setExpanded] = useState(false)
  if (!thinking) return null
  return (
    <div style={{ marginBottom: 8 }}>
      <div
        onClick={() => setExpanded(!expanded)}
        style={{
          display: 'inline-flex', alignItems: 'center', gap: 4,
          padding: '2px 8px', borderRadius: 6, cursor: 'pointer',
          background: '#f0f0f0', border: '1px solid #e0e0e0',
          fontSize: 12, color: '#666', userSelect: 'none',
        }}
      >
        <CaretRightOutlined style={{ fontSize: 10, transition: 'transform 0.2s', transform: expanded ? 'rotate(90deg)' : 'none' }} />
        <span>思考过程</span>
      </div>
      {expanded && (
        <div style={{
          marginTop: 6, padding: '8px 12px', borderRadius: 8,
          background: '#f9f9f9', border: '1px solid #eee',
          fontSize: 12, color: '#888', lineHeight: 1.6,
          maxHeight: 300, overflow: 'auto', whiteSpace: 'pre-wrap',
        }}>
          {thinking}
        </div>
      )}
    </div>
  )
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
            <ThinkingBlock thinking={message.thinking ?? ''} />
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
                // ◆ 替换为前端 UI icon
                p({ children }) {
                  return <p>{renderIconMarkers(children)}</p>
                },
                strong({ children }) {
                  return <strong>{renderIconMarkers(children)}</strong>
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

        {/* AI 反馈按钮 + 纠正意图 — 仅在消息完成后显示 */}
        {isAssistant && message.completed && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            {onFeedback && (
              <FeedbackButtons
                messageId={message.id}
                feedback={message.feedback}
                onFeedback={onFeedback}
              />
            )}
            <IntentCorrectionButton
              originalIntent={message.content}
              intentRoute={message.metadata?.intentRoute?.module}
            />
          </div>
        )}
      </div>
    </div>
  )
}
