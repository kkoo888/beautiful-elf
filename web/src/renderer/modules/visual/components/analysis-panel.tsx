import React, { useState } from 'react'
import { Segmented, Progress, Button, Typography, Empty, Spin, App } from 'antd'
import { CopyOutlined, EyeOutlined, FileTextOutlined, CodeOutlined } from '@ant-design/icons'
import type { AnalysisResult, AnalysisMode } from '../types/visual'

const { Text, Paragraph } = Typography

interface AnalysisPanelProps {
  result: AnalysisResult | null
  loading: boolean
  onModeChange?: (mode: AnalysisMode) => void
}

const modeOptions = [
  { label: '通用', value: 'general', icon: <EyeOutlined /> },
  { label: '文字', value: 'text', icon: <FileTextOutlined /> },
  { label: '代码', value: 'code', icon: <CodeOutlined /> },
]

export const AnalysisPanel: React.FC<AnalysisPanelProps> = ({ result, loading, onModeChange }) => {
  const { message } = App.useApp()
  const [mode, setMode] = useState<AnalysisMode>('general')

  const handleModeChange = (val: string | number) => {
    const newMode = val as AnalysisMode
    setMode(newMode)
    onModeChange?.(newMode)
  }

  const handleCopy = async () => {
    if (!result?.result) return
    try {
      await navigator.clipboard.writeText(result.result)
      message.success('已复制到剪贴板')
    } catch {
      message.error('复制失败')
    }
  }

  return (
    <div className="analysis-panel">
      <div className="analysis-panel-header">
        <Segmented options={modeOptions} value={mode} onChange={handleModeChange} size="small" />
      </div>

      <div className="analysis-panel-content">
        {loading ? (
          <div className="analysis-panel-loading">
            <Spin tip="分析中..." />
          </div>
        ) : result ? (
          <>
            <Paragraph
              className="analysis-panel-result"
              style={{
                background: '#1e1e2e',
                padding: 16,
                borderRadius: 8,
                maxHeight: 300,
                overflow: 'auto',
                whiteSpace: 'pre-wrap',
                fontSize: 13,
              }}
            >
              {result.result}
            </Paragraph>

            <div className="analysis-panel-confidence">
              <Text type="secondary" style={{ fontSize: 12 }}>
                置信度
              </Text>
              <Progress
                percent={Math.round(result.confidence * 100)}
                size="small"
                status="active"
                strokeColor={result.confidence > 0.9 ? '#52c41a' : '#faad14'}
              />
            </div>

            <Button icon={<CopyOutlined />} onClick={handleCopy} block style={{ marginTop: 12 }}>
              复制结果
            </Button>
          </>
        ) : (
          <Empty description="请先截图以开始分析" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        )}
      </div>
    </div>
  )
}
