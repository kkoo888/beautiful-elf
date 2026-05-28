/**
 * 翻译原文输入组件
 * 包含文本输入区域、字数统计、翻译按钮
 */

import React, { useCallback } from 'react'
import { Button, Tooltip } from 'antd'
import { SendOutlined, ClearOutlined } from '@ant-design/icons'
import styles from './translate-panel.module.css'
import type { TranslateMode } from '../types/translate'

interface TranslateInputProps {
  /** 源文本 */
  value: string
  /** 文本变更 */
  onChange: (text: string) => void
  /** 翻译模式 */
  mode: TranslateMode
  /** 翻译模式变更 */
  onModeChange: (mode: TranslateMode) => void
  /** 是否正在翻译 */
  isTranslating: boolean
  /** 执行翻译 */
  onTranslate: () => void
  /** 清空输入 */
  onClear: () => void
}

/**
 * 翻译原文输入面板
 * 包含文本区域、模式切换、字数统计、翻译按钮
 */
export const TranslateInput: React.FC<TranslateInputProps> = ({
  value,
  onChange,
  mode,
  onModeChange,
  isTranslating,
  onTranslate,
  onClear
}) => {
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      // Ctrl/Cmd + Enter 触发翻译
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault()
        onTranslate()
      }
    },
    [onTranslate]
  )

  return (
    <div className={styles.inputPanel}>
      {/* 模式切换 */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '8px 16px',
          borderBottom: '1px solid var(--color-border-secondary, #f0f0f0)'
        }}
      >
        <div className={styles.modeToggle}>
          <button
            className={`${styles.modeButton} ${mode === 'general' ? styles.modeButtonActive : ''}`}
            onClick={() => onModeChange('general')}
          >
            🌐 通用翻译
          </button>
          <button
            className={`${styles.modeButton} ${mode === 'terminology' ? styles.modeButtonActive : ''}`}
            onClick={() => onModeChange('terminology')}
          >
            📚 术语翻译
          </button>
        </div>
        <Tooltip title="清空">
          <Button
            type="text"
            size="small"
            icon={<ClearOutlined />}
            onClick={onClear}
            disabled={!value}
          />
        </Tooltip>
      </div>

      {/* 输入区域 */}
      <textarea
        className={styles.textarea}
        placeholder="输入要翻译的文本..."
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
      />

      {/* 底部操作栏 */}
      <div className={styles.inputFooter}>
        <span className={styles.charCount}>{value.length} 字符</span>
        <button
          className={styles.translateButton}
          onClick={onTranslate}
          disabled={!value.trim() || isTranslating}
        >
          <SendOutlined />
          {isTranslating ? '翻译中...' : '翻译'}
        </button>
      </div>
    </div>
  )
}
