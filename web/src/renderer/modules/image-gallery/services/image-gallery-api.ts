/**
 * 图片画廊 API 服务
 */

import { apiClient, extractData, extractPaginated } from '@/services/api-client'
import type {
  ImageGallery, ImageGalleryFormInput, ImageGalleryUpdateInput,
  ImageGenerateInput, ImageGenerateResult,
} from '../types'

const BASE = '/image_gallery'

// ─── 图片 CRUD ──────────────────────────────────────────

export async function fetchImages(params?: {
  tag?: string; enabled?: number; page?: number; pageSize?: number
}): Promise<{ items: ImageGallery[]; total: number }> {
  const { items, total } = extractPaginated(await apiClient.get(BASE, {
    params: { tag: params?.tag, enabled: params?.enabled, page: params?.page, pageSize: params?.pageSize },
  }) as any)
  return { items, total }
}

export async function fetchImageTags(): Promise<string[]> {
  return extractData(await apiClient.get(`${BASE}/tags`))
}

export async function fetchImageById(id: number): Promise<ImageGallery> {
  return extractData(await apiClient.get(`${BASE}/${id}`))
}

export async function createImage(input: ImageGalleryFormInput): Promise<ImageGallery> {
  return extractData(await apiClient.post(BASE, input))
}

export async function updateImage(id: number, input: ImageGalleryUpdateInput): Promise<ImageGallery> {
  return extractData(await apiClient.put(`${BASE}/${id}`, input))
}

export async function deleteImage(id: number): Promise<void> {
  await apiClient.delete(`${BASE}/${id}`)
}

// ─── 图片生成 ──────────────────────────────────────────

export async function generateImage(input: ImageGenerateInput): Promise<ImageGenerateResult> {
  return extractData(await apiClient.post(`${BASE}/generate`, input, { timeout: 180000 }))
}

// ─── 图片提示词生成 ─────────────────────────────────────

export async function generateImagePrompt(content: string): Promise<string> {
  return extractData(await apiClient.post(`${BASE}/generate-prompt`, { content }))
}
