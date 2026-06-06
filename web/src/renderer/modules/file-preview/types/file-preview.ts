export type FilePreviewType = 'text' | 'code' | 'image' | 'pdf' | 'unknown'

export interface FilePreviewData {
  name: string
  type: FilePreviewType
  size: number
  content?: string
  url?: string
}
