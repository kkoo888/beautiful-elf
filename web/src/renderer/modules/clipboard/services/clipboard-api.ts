/**
 * 剪贴板 API 服务
 *
 * 后端 Query 参数: page, page_size → 前端发 page_size
 * 后端 CamelModel 请求体: populate_by_name=True → 同时接受 camelCase
 */

import { apiClient, extractData } from '@/services/api-client'
import type { ClipboardItem, ClipboardListParams, ClipboardListResponse } from '../types/clipboard'

function mapContentType(ct: number): ClipboardItem['contentType'] {
  switch (ct) { case 1: return 'code'; case 2: return 'image'; case 3: return 'link'; default: return 'text' }
}

function unmapContentType(ct: ClipboardItem['contentType']): number {
  switch (ct) { case 'code': return 1; case 'image': return 2; case 'link': return 3; default: return 0 }
}

/** 获取剪贴板列表 */
export async function fetchClipboardList(params: ClipboardListParams = {}): Promise<ClipboardListResponse> {
  const { page = 1, pageSize = 20, keyword } = params
  const items = extractData(await apiClient.get('/clipboard_items', {
    params: { page, pageSize: pageSize },
  })) as any[]

  const mapped: ClipboardItem[] = items.map((item) => ({
    id: String(item.id), content: item.content, contentType: mapContentType(item.contentType),
    isPinned: item.pinned === 1, copiedAt: item.updatedAt ?? item.createdAt ?? new Date().toISOString(),
    createdAt: item.createdAt ?? new Date().toISOString(),
  }))

  let filtered = mapped
  if (keyword) {
    const lower = keyword.toLowerCase()
    filtered = mapped.filter((item) => item.content.toLowerCase().includes(lower))
  }
  filtered.sort((a, b) => (a.isPinned !== b.isPinned ? (a.isPinned ? -1 : 1) : 0))

  return { items: filtered, total: filtered.length, page, pageSize }
}

/** 新增剪贴板条目 */
export async function createClipboardItem(
  data: Pick<ClipboardItem, 'content' | 'contentType' | 'language'>
): Promise<ClipboardItem> {
  const raw = extractData(await apiClient.post('/clipboard_items', {
    content: data.content, contentType: unmapContentType(data.contentType),
  })) as any
  return { ...raw, id: String(raw.id), contentType: mapContentType(raw.contentType), isPinned: raw.pinned === 1 }
}

/** 删除剪贴板条目 */
export async function deleteClipboardItem(id: string): Promise<void> {
  await apiClient.delete(`/clipboard_items/${id}`)
}

/** 固定/取消固定 */
export async function togglePinClipboardItem(id: string): Promise<ClipboardItem> {
  const raw = extractData(await apiClient.put(`/clipboard_items/${id}/pin`)) as any
  return { ...raw, id: String(raw.id), contentType: mapContentType(raw.contentType), isPinned: raw.pinned === 1 }
}
