/**
 * 翻译译文输出组件
 * 显示翻译结果、术语高亮、复制功能
 */

import React, { useCallback, useState } from 'react'
import { Button, Tooltip, message } from 'antd'
import { CopyOutlined, CheckOutlined } from '@ant-design/icons'
import styles from './translate-panel.module.css'
import { TermBadgeList, TermHighlightText } from './term-badge'
import type { TranslateResult } from '../types/translate'

interface TranslateOutputProps {
  /** 翻译结果 */
  result: TranslateResult | null
  /** 是否正在翻译 */
  isTranslating: boolean
}

/**
 * 翻译译文输出面板
 * 展示翻译结果，支持术语高亮和一键复制
 */
export const TranslateOutput: React.FC<TranslateOutputProps> = ({ result, isTranslating }) => {
  const [copied, setCopied] = useState(false)

  /** 复制译文到剪贴板 */
  const handleCopy = useCallback(async () => {
    if (!result?.targetText) return
    try {
      await navigator.clipboard.writeText(result.targetText)
      setCopied(true)
      message.success('已复制到剪贴板')
      setTimeout(() => setCopied(false), 2000)
    } catch {
      message.error('复制失败')
    }
  }, [result?.targetText])

  // 加载中状态
  if (isTranslating) {
    return (
      <div className={styles.outputPanel}>
        <div className={styles.loadingContainer}>
          <div className={styles.spinner} />
          <span className={styles.loadingText}>正在翻译...</span>
        </div>
      </div>
    )
  }

  // 空状态
  if (!result) {
    return (
      <div className={styles.outputPanel}>
        <div className={styles.emptyState}>
          <span className={styles.emptyIcon}>🌐</span>
          <span className={styles.emptyText}>输入文本开始翻译</span>
          <span className={styles.emptySubtext}>支持多种语言互译，术语模式可识别专业词汇</span>
        </div>
      </div>
    )
  }

  const hasTermHits = result.termHits && result.termHits.length > 0

  return (
    <div className={styles.outputPanel}>
      {/* 译文内容 */}
      <div className={`${styles.outputContent} ${styles.fadeIn}`}>
        {hasTermHits ? (
          <TermHighlightText text={result.targetText} termHits={result.termHits!} />
        ) : (
          result.targetText
        )}
      </div>

      {/* 术语标记 */}
      {hasTermHits && <TermBadgeList termHits={result.termHits!} />}

      {/* 底部操作栏 */}
      <div className={styles.outputFooter}>
        <Tooltip title={copied ? '已复制' : '复制译文'}>
          <button className={styles.copyButton} onClick={handleCopy}>
            {copied ? <CheckOutlined /> : <CopyOutlined />}
            {copied ? '已复制' : '复制'}
          </button>
        </Tooltip>
      </div>
    </div>
  )
}
