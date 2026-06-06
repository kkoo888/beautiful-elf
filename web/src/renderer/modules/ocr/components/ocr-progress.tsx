import React from 'react'
import { Progress, Alert } from 'antd'
import type { OcrProgress } from '../types/ocr'

interface OcrProgressProps {
  progress: OcrProgress
}

const OcrProgressView: React.FC<OcrProgressProps> = ({ progress }) => {
  if (progress.status === 'idle') return null

  if (progress.status === 'error') {
    return <Alert type="error" message="识别失败，请重试" showIcon />
  }

  return (
    <Progress
      percent={progress.progress}
      status={progress.status === 'done' ? 'success' : 'active'}
    />
  )
}

export default OcrProgressView
