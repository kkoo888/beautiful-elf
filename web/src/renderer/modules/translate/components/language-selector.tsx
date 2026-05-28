/**
 * 语言选择器组件
 * 支持源语言（含自动检测）和目标语言选择
 */

import React from 'react'
import { Select, Space } from 'antd'
import { SwapOutlined } from '@ant-design/icons'
import styles from './translate-panel.module.css'
import type { Language, DetectResult } from '../types/translate'

interface LanguageSelectorProps {
  /** 支持的语言列表 */
  languages: Language[]
  /** 源语言 */
  sourceLang: string
  /** 目标语言 */
  targetLang: string
  /** 语言检测结果 */
  detectedLang: DetectResult | null
  /** 源语言变更 */
  onSourceLangChange: (lang: string) => void
  /** 目标语言变更 */
  onTargetLangChange: (lang: string) => void
  /** 交换语言 */
  onSwap: () => void
}

/**
 * 语言选择器
 * 双侧下拉 + 中间交换按钮
 */
export const LanguageSelector: React.FC<LanguageSelectorProps> = ({
  languages,
  sourceLang,
  targetLang,
  detectedLang,
  onSourceLangChange,
  onTargetLangChange,
  onSwap,
}) => {
  const sourceLanguages = languages
  const targetLanguages = languages.filter((l) => l.code !== 'auto')

  // 自动检测时显示检测到的语言名称
  const detectedName = detectedLang
    ? languages.find((l) => l.code === detectedLang.lang)?.name
    : null

  return (
    <div className={styles.languageBar}>
      {/* 源语言 */}
      <div className={styles.langSelectWrapper}>
        <Select
          className={styles.langSelect}
          value={sourceLang}
          onChange={onSourceLangChange}
          options={sourceLanguages.map((l) => ({
            value: l.code,
            label: l.name,
          }))}
          size="small"
        />
        {sourceLang === 'auto' && detectedName && (
          <span className={styles.detectedBadge}>🔍 {detectedName}</span>
        )}
      </div>

      {/* 交换按钮 */}
      <button
        className={styles.swapButton}
        onClick={onSwap}
        disabled={sourceLang === 'auto'}
        title={sourceLang === 'auto' ? '自动检测模式下无法交换' : '交换语言'}
      >
        <SwapOutlined />
      </button>

      {/* 目标语言 */}
      <div className={styles.langSelectWrapper}>
        <Select
          className={styles.langSelect}
          value={targetLang}
          onChange={onTargetLangChange}
          options={targetLanguages.map((l) => ({
            value: l.code,
            label: l.name,
          }))}
          size="small"
        />
      </div>
    </div>
  )
}
