import { useState, useCallback } from 'react'
import type { CaptureMode, CaptureResult } from '../types/visual'
import { captureScreen } from '../services/visual-api'

export function useCapture() {
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<CaptureResult | null>(null)

  const capture = useCallback(async (mode: CaptureMode) => {
    setLoading(true)
    try {
      // Electron 环境由 captureScreen 内部自动走 desktopCapturer
      const data = await captureScreen(mode)
      setResult(data)
      return data
    } catch (err) {
      console.error('[useCapture] capture failed:', err)
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  const clear = useCallback(() => {
    setResult(null)
  }, [])

  return { loading, result, capture, clear }
}
