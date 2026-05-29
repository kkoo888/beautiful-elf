import { apiClient } from '@/services/api-client'
import type { ClipboardItem, ClipboardListParams, ClipboardListResponse } from '../types/clipboard'

// ── 类型映射：后端 snake_case ↔ 前端 camelCase ──────────────────

interface BackendClipboardItem {
  id: number
  content: string
  content_type: number
  pinned: number
  source_app: string
  created_at: string | null
  updated_at: string | null
}

/** 后端 content_type 数字 → 前端 contentType 字符串 */
function mapContentType(ct: number): ClipboardItem['contentType'] {
  switch (ct) {
    case 1: return 'code'
    case 2: return 'image'
    case 3: return 'link'
    default: return 'text'
  }
}

/** 前端 contentType 字符串 → 后端 content_type 数字 */
function unmapContentType(ct: ClipboardItem['contentType']): number {
  switch (ct) {
    case 'code': return 1
    case 'image': return 2
    case 'link': return 3
    default: return 0
  }
}

function toFrontend(item: BackendClipboardItem): ClipboardItem {
  return {
    id: String(item.id),
    content: item.content,
    contentType: mapContentType(item.content_type),
    isPinned: item.pinned === 1,
    copiedAt: item.updated_at ?? item.created_at ?? new Date().toISOString(),
    createdAt: item.created_at ?? new Date().toISOString(),
  }
}

// ── API 函数 ──────────────────────────────────────────────────

/** 获取剪贴板列表 */
export async function fetchClipboardList(
  params: ClipboardListParams = {}
): Promise<ClipboardListResponse> {
  const { page = 1, pageSize = 20, keyword } = params
  const resp = await apiClient.get('/clipboard-items', {
    params: { page, page_size: pageSize },
  })
  const body = resp.data as any
  const items: ClipboardItem[] = (body.data ?? []).map(toFrontend)

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
    pageSize: body.page_size ?? pageSize,
  }
}

/** 新增剪贴板条目 */
export async function createClipboardItem(
  data: Pick<ClipboardItem, 'content' | 'contentType' | 'language'>
): Promise<ClipboardItem> {
  const resp = await apiClient.post('/clipboard-items', {
    content: data.content,
    content_type: unmapContentType(data.contentType),
  })
  return toFrontend((resp.data as any).data)
}

/** 删除剪贴板条目 */
export async function deleteClipboardItem(id: string): Promise<void> {
  await apiClient.delete(`/clipboard-items/${id}`)
}

/** 固定/取消固定 */
export async function togglePinClipboardItem(id: string): Promise<ClipboardItem> {
  const resp = await apiClient.put(`/clipboard-items/${id}/pin`)
  return toFrontend((resp.data as any).data)
}
