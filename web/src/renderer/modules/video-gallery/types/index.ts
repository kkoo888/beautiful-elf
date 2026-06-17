/** 视频画廊类型定义 */

export interface VideoGallery {
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
  numFrames: number
  frameRate: number
  duration: number
  isEnabled: number
  createdAt: string | null
  updatedAt: string | null
}

export interface VideoGalleryFormInput {
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
  numFrames?: number
  frameRate?: number
  duration?: number
}

export interface VideoGalleryUpdateInput {
  name?: string
  prompt?: string
  negativePrompt?: string
  tags?: string
  isEnabled?: number
}

export interface VideoGenerateInput {
  prompt: string
  negativePrompt?: string
  modelName?: string
  providerId?: number
  image?: string
  images?: string[]
  mode?: string
  width?: number
  height?: number
  numFrames?: number
  frameRate?: number
  numInferenceSteps?: number
  seed?: number
}

export interface VideoGenerateResult {
  name: string
  filePath: string
  thumbnailPath: string
  width: number
  height: number
  numFrames: number
  frameRate: number
  duration: number
}
