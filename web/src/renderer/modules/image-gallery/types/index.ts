/** 图片画廊类型定义 */

export interface ImageGallery {
  id: number
  name: string
  prompt: string
  negativePrompt: string
  modelName: string
  providerId: number
  filePath: string
  thumbnailPath: string
  tags: string
  width: number
  height: number
  isEnabled: number
  createdAt: string | null
  updatedAt: string | null
}

export interface ImageGalleryFormInput {
  name?: string
  prompt: string
  negativePrompt?: string
  modelName?: string
  providerId?: number
  filePath: string
  thumbnailPath?: string
  tags?: string
  width?: number
  height?: number
}

export interface ImageGalleryUpdateInput {
  name?: string
  prompt?: string
  negativePrompt?: string
  tags?: string
  isEnabled?: number
}

export interface ImageGenerateInput {
  prompt: string
  negativePrompt?: string
  modelName?: string
  providerId?: number
  width?: number
  height?: number
}

export interface ImageGenerateResult {
  name: string
  filePath: string
  thumbnailPath: string
  width: number
  height: number
}
