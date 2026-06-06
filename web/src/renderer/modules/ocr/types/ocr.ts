export interface OcrResult {
  text: string
  confidence: number
  language: string
}

export interface OcrProgress {
  status: 'idle' | 'loading' | 'done' | 'error'
  progress: number
}

export interface OcrHistoryItem {
  id: string
  imageName: string
  text: string
  confidence: number
  createdAt: number
}
