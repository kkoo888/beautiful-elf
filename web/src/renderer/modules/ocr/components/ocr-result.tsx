import React from 'react'
import { Button, Progress, Typography, message } from 'antd'
import { CopyOutlined } from '@ant-design/icons'
import type { OcrResult } from '../types/ocr'

const { Paragraph } = Typography

interface OcrResultProps {
  result: OcrResult | null
}

const OcrResultView: React.FC<OcrResultProps> = ({ result }) => {
  if (!result) return null

  const confidencePercent = Math.round(result.confidence * 100)

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(result.text)
      message.success('已复制到剪贴板')
    } catch {
      message.error('复制失败，请手动选择复制')
    }
  }

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <span style={{ marginRight: 8 }}>置信度：</span>
        <Progress
          percent={confidencePercent}
          status={confidencePercent >= 80 ? 'success' : 'normal'}
          style={{ display: 'inline-block', width: 200 }}
        />
      </div>

      <div style={{ marginBottom: 8 }}>
        <span>识别语言：{result.language}</span>
      </div>

      <Paragraph
        style={{
          background: '#f5f5f5',
          padding: 16,
          borderRadius: 8,
          whiteSpace: 'pre-wrap',
          maxHeight: 300,
          overflow: 'auto',
        }}
      >
        {result.text}
      </Paragraph>

      <Button type="primary" icon={<CopyOutlined />} onClick={handleCopy}>
        复制文本
      </Button>
    </div>
  )
}

export default OcrResultView
