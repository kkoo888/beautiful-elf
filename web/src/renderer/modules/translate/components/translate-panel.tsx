/**
 * 翻译主面板组件
 * 整合语言选择、输入输出、翻译历史
 */

import React, { useCallback } from 'react'
import styles from './translate-panel.module.css'
import { LanguageSelector } from './language-selector'
import { TranslateInput } from './translate-input'
import { TranslateOutput } from './translate-output'
import { TranslateHistory } from './translate-history'
import { useTranslate } from '../hooks/use-translate'
import type { TranslateResult } from '../types/translate'

/**
 * 翻译主面板
 * 双栏布局：左侧原文输入，右侧译文输出，右侧历史记录
 */
export const TranslatePanel: React.FC = () => {
  const {
    sourceText,
    setSourceText,
    sourceLang,
    setSourceLang,
    targetLang,
    setTargetLang,
    mode,
    setMode,
    isTranslating,
    result,
    history,
    isLoadingHistory,
    languages,
    detectedLang,
    doTranslate,
    swapLanguages,
    loadHistory,
    handleFavorite,
    clearInput,
  } = useTranslate()

  /** 从历史记录回填 */
  const handleSelectHistory = useCallback(
    (item: TranslateResult) => {
      setSourceText(item.sourceText)
      setSourceLang(item.sourceLang)
      setTargetLang(item.targetLang)
      setMode(item.mode)
    },
    [setSourceText, setSourceLang, setTargetLang, setMode]
  )

  return (
    <div className={styles.translatePanel}>
      {/* 顶部标题栏 */}
      <div className={styles.header}>
        <h4 className={styles.title}>🌐 翻译</h4>
        <div className={styles.headerActions}>
          <span style={{ fontSize: 12, color: 'var(--color-text-secondary, #888)' }}>
            Ctrl+Enter 翻译
          </span>
        </div>
      </div>

      {/* 语言选择栏 */}
      <LanguageSelector
        languages={languages}
        sourceLang={sourceLang}
        targetLang={targetLang}
        detectedLang={detectedLang}
        onSourceLangChange={setSourceLang}
        onTargetLangChange={setTargetLang}
        onSwap={swapLanguages}
      />

      {/* 主内容区域 */}
      <div className={styles.mainContent}>
        {/* 左侧：原文输入 */}
        <TranslateInput
          value={sourceText}
          onChange={setSourceText}
          mode={mode}
          onModeChange={setMode}
          isTranslating={isTranslating}
          onTranslate={doTranslate}
          onClear={clearInput}
        />

        {/* 右侧：译文输出 */}
        <TranslateOutput result={result} isTranslating={isTranslating} />

        {/* 历史记录侧边栏 */}
        <TranslateHistory
          history={history}
          isLoading={isLoadingHistory}
          languages={languages}
          onLoad={loadHistory}
          onSelect={handleSelectHistory}
          onFavorite={handleFavorite}
        />
      </div>
    </div>
  )
}
