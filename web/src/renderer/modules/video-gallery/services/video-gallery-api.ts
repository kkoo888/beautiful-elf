/**
 * 视频画廊 API 服务
 */

import { apiClient, extractData, extractPaginated } from '@/services/api-client'
import type {
  VideoGallery, VideoGalleryFormInput, VideoGalleryUpdateInput,
  VideoGenerateInput, VideoGenerateResult,
} from '../types'

const BASE = '/video_gallery'

// ─── 视频 CRUD ──────────────────────────────────────────

export async function fetchVideos(params?: {
  tag?: string; enabled?: number; page?: number; pageSize?: number
}): Promise<{ items: VideoGallery[]; total: number }> {
  const { items, total } = extractPaginated(await apiClient.get(BASE, {
    params: { tag: params?.tag, enabled: params?.enabled, page: params?.page, pageSize: params?.pageSize },
  }) as any)
  return { items, total }
}

export async function fetchVideoTags(): Promise<string[]> {
  return extractData(await apiClient.get(`${BASE}/tags`))
}

export async function fetchVideoById(id: number): Promise<VideoGallery> {
  return extractData(await apiClient.get(`${BASE}/${id}`))
}

export async function createVideo(input: VideoGalleryFormInput): Promise<VideoGallery> {
  return extractData(await apiClient.post(BASE, input))
}

export async function updateVideo(id: number, input: VideoGalleryUpdateInput): Promise<VideoGallery> {
  return extractData(await apiClient.put(`${BASE}/${id}`, input))
}

export async function deleteVideo(id: number): Promise<void> {
  await apiClient.delete(`${BASE}/${id}`)
}

// ─── 视频生成 ──────────────────────────────────────────

export async function generateVideo(input: VideoGenerateInput): Promise<VideoGenerateResult> {
  return extractData(await apiClient.post(`${BASE}/generate`, input, { timeout: 600000 }))
}

// ─── 视频提示词生成 ─────────────────────────────────────

export async function generateVideoPrompt(content: string): Promise<string> {
  return extractData(await apiClient.post(`${BASE}/generate-prompt`, { content }))
}
