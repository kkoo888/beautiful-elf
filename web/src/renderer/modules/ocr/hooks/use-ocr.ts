import { useState, useCallback } from 'react'
import type { OcrResult, OcrProgress, OcrHistoryItem } from '../types/ocr'
import { recognizeText } from '../services/ocr-api'

const HISTORY_KEY = 'ocr-history'
const MAX_HISTORY = 10

function loadHistory(): OcrHistoryItem[] {
  try {
    const raw = localStorage.getItem(HISTORY_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

function saveHistory(items: OcrHistoryItem[]) {
  localStorage.setItem(HISTORY_KEY, JSON.stringify(items.slice(0, MAX_HISTORY)))
}

export function useOcr() {
  const [progress, setProgress] = useState<OcrProgress>({ status: 'idle', progress: 0 })
  const [result, setResult] = useState<OcrResult | null>(null)
  const [history, setHistory] = useState<OcrHistoryItem[]>(loadHistory)

  const recognize = useCallback(
    async (imageData: string, imageName = '未命名图片') => {
      setProgress({ status: 'loading', progress: 0 })
      setResult(null)

      // 模拟进度
      const timer = setInterval(() => {
        setProgress((prev) => {
          if (prev.progress >= 90) return prev
          return { ...prev, progress: prev.progress + 10 }
        })
      }, 200)

      try {
        const ocrResult = await recognizeText(imageData)
        clearInterval(timer)
        setProgress({ status: 'done', progress: 100 })
        setResult(ocrResult)

        // 保存历史
        const newItem: OcrHistoryItem = {
          id: Date.now().toString(),
          imageName,
          text: ocrResult.text,
          confidence: ocrResult.confidence,
          createdAt: Date.now(),
        }
        const updated = [newItem, ...history].slice(0, MAX_HISTORY)
        setHistory(updated)
        saveHistory(updated)
      } catch {
        clearInterval(timer)
        setProgress({ status: 'error', progress: 0 })
      }
    },
    [history]
  )

  const clearHistory = useCallback(() => {
    setHistory([])
    localStorage.removeItem(HISTORY_KEY)
  }, [])

  return { progress, result, history, recognize, clearHistory }
}
