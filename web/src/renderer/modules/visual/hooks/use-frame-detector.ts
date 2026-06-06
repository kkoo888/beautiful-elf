import { useRef, useCallback } from 'react'

export interface FrameDetectionResult {
  changePercent: number
  isChanged: boolean
}

/**
 * 逐像素比较两帧 Canvas ImageData
 * threshold: 像素差异阈值 (1-20)，超过此值视为变化像素
 */
export function useFrameDetector(threshold: number = 10) {
  const prevFrameRef = useRef<ImageData | null>(null)

  const detect = useCallback(
    (currentFrame: ImageData): FrameDetectionResult => {
      const prev = prevFrameRef.current
      prevFrameRef.current = currentFrame

      if (!prev) {
        return { changePercent: 0, isChanged: false }
      }

      const { data: currData } = currentFrame
      const { data: prevData } = prev

      if (currData.length !== prevData.length) {
        return { changePercent: 100, isChanged: true }
      }

      const totalPixels = currData.length / 4
      let changedPixels = 0

      for (let i = 0; i < currData.length; i += 4) {
        const dr = Math.abs(currData[i] - prevData[i])
        const dg = Math.abs(currData[i + 1] - prevData[i + 1])
        const db = Math.abs(currData[i + 2] - prevData[i + 2])
        // 忽略 alpha 通道
        const diff = (dr + dg + db) / 3

        if (diff > threshold) {
          changedPixels++
        }
      }

      const changePercent = (changedPixels / totalPixels) * 100
      const isChanged = changePercent > 1 // 超过 1% 像素变化视为帧变化

      return { changePercent, isChanged }
    },
    [threshold]
  )

  const reset = useCallback(() => {
    prevFrameRef.current = null
  }, [])

  return { detect, reset }
}
