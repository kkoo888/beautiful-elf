/**
 * 翻译状态管理 Hook
 * 管理翻译输入、结果、历史等状态
 */

import { useState, useCallback, useEffect, useRef } from 'react'
import {
  translate as translateApi,
  fetchHistory,
  fetchLanguages,
  detectLanguage,
  toggleFavorite
} from '../services/translate-api'
import type {
  TranslateResult,
  TranslateMode,
  Language,
  DetectResult
} from '../types/translate'

interface UseTranslateReturn {
  /** 源文本 */
  sourceText: string
  /** 设置源文本 */
  setSourceText: (text: string) => void
  /** 源语言 */
  sourceLang: string
  /** 设置源语言 */
  setSourceLang: (lang: string) => void
  /** 目标语言 */
  targetLang: string
  /** 设置目标语言 */
  setTargetLang: (lang: string) => void
  /** 翻译模式 */
  mode: TranslateMode
  /** 设置翻译模式 */
  setMode: (mode: TranslateMode) => void
  /** 是否正在翻译 */
  isTranslating: boolean
  /** 当前翻译结果 */
  result: TranslateResult | null
  /** 翻译历史 */
  history: TranslateResult[]
  /** 是否正在加载历史 */
  isLoadingHistory: boolean
  /** 支持的语言列表 */
  languages: Language[]
  /** 语言检测结果 */
  detectedLang: DetectResult | null
  /** 执行翻译 */
  doTranslate: () => Promise<void>
  /** 交换语言 */
  swapLanguages: () => void
  /** 加载历史 */
  loadHistory: () => Promise<void>
  /** 收藏/取消收藏 */
  handleFavorite: (id: string, favorite: boolean) => Promise<void>
  /** 清空输入 */
  clearInput: () => void
}

export function useTranslate(): UseTranslateReturn {
  const [sourceText, setSourceText] = useState('')
  const [sourceLang, setSourceLang] = useState('auto')
  const [targetLang, setTargetLang] = useState('en')
  const [mode, setMode] = useState<TranslateMode>('general')
  const [isTranslating, setIsTranslating] = useState(false)
  const [result, setResult] = useState<TranslateResult | null>(null)
  const [history, setHistory] = useState<TranslateResult[]>([])
  const [isLoadingHistory, setIsLoadingHistory] = useState(false)
  const [languages, setLanguages] = useState<Language[]>([])
  const [detectedLang, setDetectedLang] = useState<DetectResult | null>(null)

  const detectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  /** 加载语言列表 */
  useEffect(() => {
    fetchLanguages().then(setLanguages).catch(console.error)
  }, [])

  /** 自动检测语言（防抖） */
  useEffect(() => {
    if (detectTimerRef.current) {
      clearTimeout(detectTimerRef.current)
    }

    if (!sourceText.trim()) {
      setDetectedLang(null)
      return
    }

    detectTimerRef.current = setTimeout(() => {
      detectLanguage(sourceText.trim())
        .then((result) => {
          setDetectedLang(result)
          if (sourceLang === 'auto') {
            // 自动切换目标语言（避免源目标相同）
            if (result.lang === targetLang) {
              const fallback = result.lang === 'zh' ? 'en' : 'zh'
              setTargetLang(fallback)
            }
          }
        })
        .catch(console.error)
    }, 500)

    return () => {
      if (detectTimerRef.current) {
        clearTimeout(detectTimerRef.current)
      }
    }
  }, [sourceText, sourceLang, targetLang])

  /** 执行翻译 */
  const doTranslate = useCallback(async () => {
    if (!sourceText.trim() || isTranslating) return

    setIsTranslating(true)
    try {
      const res = await translateApi({
        sourceText: sourceText.trim(),
        sourceLang,
        targetLang,
        mode
      })
      setResult(res)
    } catch (error) {
      console.error('[Translate] Error:', error)
    } finally {
      setIsTranslating(false)
    }
  }, [sourceText, sourceLang, targetLang, mode, isTranslating])

  /** 交换语言 */
  const swapLanguages = useCallback(() => {
    if (sourceLang === 'auto') return

    const prevSource = sourceLang
    const prevTarget = targetLang
    setSourceLang(prevTarget)
    setTargetLang(prevSource)

    // 如果有结果，交换文本
    if (result) {
      setSourceText(result.targetText)
      setResult(null)
    }
  }, [sourceLang, targetLang, result])

  /** 加载翻译历史 */
  const loadHistory = useCallback(async () => {
    setIsLoadingHistory(true)
    try {
      const data = await fetchHistory()
      setHistory(data)
    } catch (error) {
      console.error('[Translate] Load history error:', error)
    } finally {
      setIsLoadingHistory(false)
    }
  }, [])

  /** 收藏/取消收藏 */
  const handleFavorite = useCallback(
    async (id: string, favorite: boolean) => {
      try {
        await toggleFavorite({ id, favorite })
      } catch (error) {
        console.error('[Translate] Favorite error:', error)
      }
    },
    []
  )

  /** 清空输入 */
  const clearInput = useCallback(() => {
    setSourceText('')
    setResult(null)
    setDetectedLang(null)
  }, [])

  return {
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
    clearInput
  }
}
