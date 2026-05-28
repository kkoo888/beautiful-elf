import React, { useState, useCallback } from 'react'
import { Segmented, Card, Space, Spin } from 'antd'
import { DesktopOutlined, ScanOutlined } from '@ant-design/icons'
import { CapturePreview } from './components/capture-preview'
import { AnalysisPanel } from './components/analysis-panel'
import { FrameSettings } from './components/frame-settings'
import { useCapture } from './hooks/use-capture'
import { analyzeImage } from './services/visual-api'
import type { CaptureMode, AnalysisMode, AnalysisResult, FrameChangeConfig } from './types/visual'
import styles from './visual-panel.module.css'

const captureModeOptions = [
  { label: '全屏', value: 'fullscreen', icon: <DesktopOutlined /> },
  { label: '选区', value: 'region', icon: <ScanOutlined /> },
]

export const VisualPanel: React.FC = () => {
  const [captureMode, setCaptureMode] = useState<CaptureMode>('fullscreen')
  const { loading: captureLoading, result: captureResult, capture } = useCapture()
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null)
  const [analysisLoading, setAnalysisLoading] = useState(false)
  const [frameConfig, setFrameConfig] = useState<FrameChangeConfig>({
    enabled: false,
    threshold: 10,
    sensitivity: 'medium',
  })

  const handleCapture = useCallback(async () => {
    const data = await capture(captureMode)
    if (data) {
      setAnalysisLoading(true)
      try {
        const result = await analyzeImage(data.imageData, 'general')
        result.captureId = data.id
        setAnalysisResult(result)
      } finally {
        setAnalysisLoading(false)
      }
    }
  }, [capture, captureMode])

  const handleCaptureModeChange = (val: string | number) => {
    setCaptureMode(val as CaptureMode)
  }

  const handleAnalysisModeChange = useCallback(
    async (mode: AnalysisMode) => {
      if (!captureResult) return
      setAnalysisLoading(true)
      try {
        const result = await analyzeImage(captureResult.imageData, mode)
        result.captureId = captureResult.id
        setAnalysisResult(result)
      } finally {
        setAnalysisLoading(false)
      }
    },
    [captureResult]
  )

  return (
    <div className={styles.panel}>
      {/* 顶部：截图模式选择 */}
      <div className={styles.header}>
        <Segmented
          options={captureModeOptions}
          value={captureMode}
          onChange={handleCaptureModeChange}
        />
        {captureLoading && <Spin size="small" />}
      </div>

      {/* 主体：左侧截图 + 右侧分析 */}
      <div className={styles.body}>
        <Card className={styles.left} size="small" title="截图预览">
          <CapturePreview capture={captureResult} onRecapture={handleCapture} />
        </Card>

        <Card className={styles.right} size="small" title="分析结果">
          <AnalysisPanel
            result={analysisResult}
            loading={analysisLoading}
            onModeChange={handleAnalysisModeChange}
          />
        </Card>
      </div>

      {/* 底部：帧变化检测设置 */}
      <Card className={styles.footer} size="small" title="帧变化检测">
        <FrameSettings config={frameConfig} onChange={setFrameConfig} />
      </Card>
    </div>
  )
}
