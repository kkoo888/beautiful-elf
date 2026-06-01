import { apiClient } from '@/services/api-client'
import type { PaginatedResponse } from '@/types'
import type { Snippet, SnippetFormData, SnippetQueryParams } from '../types/snippets'

// ── 类型映射：后端 snake_case ↔ 前端 camelCase ──────────────────

interface BackendSnippet {
  id: number
  title: string
  content: string
  language: string
  use_count: number
  tags: string[]
  created_at: string
  updated_at: string
}

function toFrontend(item: BackendSnippet): Snippet {
  return {
    id: String(item.id),
    title: item.title,
    content: item.content,
    language: item.language,
    tags: item.tags ?? [],
    useCount: item.use_count ?? 0,
    createdAt: item.created_at,
    updatedAt: item.updated_at,
  }
}

// ── API 函数 ──────────────────────────────────────────────────

/** 获取片段列表 */
export async function fetchSnippets(
  params?: SnippetQueryParams
): Promise<PaginatedResponse<Snippet>> {
  const resp = await apiClient.get('/snippets', {
    params: {
      page: params?.page ?? 1,
      page_size: params?.pageSize ?? 20,
      tag: params?.tags?.[0], // 后端只支持单 tag 过滤
    },
  })
  const body = resp.data as any
  let items: Snippet[] = (body.data ?? []).map(toFrontend)

  // 前端关键词过滤（后端暂不支持 keyword）
  if (params?.keyword) {
    const kw = params.keyword.toLowerCase()
    items = items.filter(
      (s) =>
        s.title.toLowerCase().includes(kw) ||
        s.content.toLowerCase().includes(kw) ||
        s.tags.some((t) => t.toLowerCase().includes(kw))
    )
  }

  // 前端多标签过滤
  if (params?.tags && params.tags.length > 1) {
    items = items.filter((s) => params.tags!.some((tag) => s.tags.includes(tag)))
  }

  // 按使用次数排序
  items.sort((a, b) => b.useCount - a.useCount)

  return {
    items,
    total: body.total ?? items.length,
    page: body.page ?? params?.page ?? 1,
    pageSize: body.page_size ?? params?.pageSize ?? 20,
  }
}

/** 创建片段 */
export async function createSnippet(data: SnippetFormData): Promise<Snippet> {
  const resp = await apiClient.post('/snippets', {
    title: data.title,
    content: data.content,
    language: data.language,
    tags: data.tags,
  })
  return toFrontend((resp.data as any).data)
}

/** 更新片段 */
export async function updateSnippet(id: string, data: SnippetFormData): Promise<Snippet> {
  const resp = await apiClient.put(`/snippets/${id}`, {
    title: data.title,
    content: data.content,
    language: data.language,
    tags: data.tags,
  })
  return toFrontend((resp.data as any).data)
}

/** 删除片段 */
export async function deleteSnippet(id: string): Promise<void> {
  await apiClient.delete(`/snippets/${id}`)
}

/** 记录使用 */
export async function recordSnippetUse(id: string): Promise<void> {
  await apiClient.post(`/snippets/${id}/use`)
}

/** 获取所有已用标签（前端聚合，后端无此接口） */
export async function fetchAllTags(): Promise<string[]> {
  // 从全量列表中聚合标签
  const resp = await apiClient.get('/snippets', { params: { page: 1, page_size: 100 } })
  const body = resp.data as any
  const items: BackendSnippet[] = body.data ?? []
  const tags = new Set<string>()
  items.forEach((s) => (s.tags ?? []).forEach((t: string) => tags.add(t)))
  return Array.from(tags).sort()
}
