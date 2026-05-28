export type CaptureMode = 'fullscreen' | 'region'
export type AnalysisMode = 'general' | 'text' | 'code'

export interface CaptureResult {
  id: string
  imageData: string // base64
  timestamp: number
  mode: CaptureMode
}

export interface AnalysisResult {
  id: string
  captureId: string
  mode: AnalysisMode
  result: string
  confidence: number
}

export interface FrameChangeConfig {
  enabled: boolean
  threshold: number // 1-20
  sensitivity: 'low' | 'medium' | 'high'
}
