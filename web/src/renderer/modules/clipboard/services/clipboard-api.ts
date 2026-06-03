/**
 * 剪贴板 API 服务
 *
 * 后端 CamelModel 已统一返回 camelCase，直接透传，无需转换。
 * contentType 映射（数字↔字符串）属于业务逻辑，保留。
 */

import { apiClient } from '@/services/api-client'
import type { ClipboardItem, ClipboardListParams, ClipboardListResponse } from '../types/clipboard'

/** 后端 contentType 数字 → 前端字符串 */
function mapContentType(ct: number): ClipboardItem['contentType'] {
  switch (ct) {
    case 1: return 'code'
    case 2: return 'image'
    case 3: return 'link'
    default: return 'text'
  }
}

/** 前端 contentType 字符串 → 后端数字 */
function unmapContentType(ct: ClipboardItem['contentType']): number {
  switch (ct) {
    case 'code': return 1
    case 'image': return 2
    case 'link': return 3
    default: return 0
  }
}

/** 获取剪贴板列表 */
export async function fetchClipboardList(
  params: ClipboardListParams = {}
): Promise<ClipboardListResponse> {
  const { page = 1, pageSize = 20, keyword } = params
  const resp = await apiClient.get('/clipboard_items', {
    params: { page, pageSize },
  })
  const body = resp.data as any
  const items: ClipboardItem[] = (body.data ?? []).map((item: any) => ({
    id: String(item.id),
    content: item.content,
    contentType: mapContentType(item.contentType),
    isPinned: item.pinned === 1,
    copiedAt: item.updatedAt ?? item.createdAt ?? new Date().toISOString(),
    createdAt: item.createdAt ?? new Date().toISOString(),
  }))

  // 前端关键词过滤（后端暂不支持 keyword 搜索）
  let filtered = items
  if (keyword) {
    const lower = keyword.toLowerCase()
    filtered = items.filter((item) => item.content.toLowerCase().includes(lower))
  }

  // 固定项排在最前
  filtered.sort((a, b) => {
    if (a.isPinned !== b.isPinned) return a.isPinned ? -1 : 1
    return 0
  })

  return {
    items: filtered,
    total: body.total ?? filtered.length,
    page: body.page ?? page,
    pageSize: body.pageSize ?? pageSize,
  }
}

/** 新增剪贴板条目 */
export async function createClipboardItem(
  data: Pick<ClipboardItem, 'content' | 'contentType' | 'language'>
): Promise<ClipboardItem> {
  const resp = await apiClient.post('/clipboard_items', {
    content: data.content,
    contentType: unmapContentType(data.contentType),
  })
  const raw = (resp.data as any).data
  return {
    ...raw,
    id: String(raw.id),
    contentType: mapContentType(raw.contentType),
    isPinned: raw.pinned === 1,
  }
}

/** 删除剪贴板条目 */
export async function deleteClipboardItem(id: string): Promise<void> {
  await apiClient.delete(`/clipboard_items/${id}`)
}

/** 固定/取消固定 */
export async function togglePinClipboardItem(id: string): Promise<ClipboardItem> {
  const resp = await apiClient.put(`/clipboard_items/${id}/pin`)
  const raw = (resp.data as any).data
  return {
    ...raw,
    id: String(raw.id),
    contentType: mapContentType(raw.contentType),
    isPinned: raw.pinned === 1,
  }
}
