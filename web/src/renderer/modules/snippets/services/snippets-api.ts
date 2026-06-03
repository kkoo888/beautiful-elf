/**
 * 代码片段 API 服务
 */

import { apiClient, extractData, extractPaginated } from '@/services/api-client'
import type { PaginatedResponse } from '@/types'
import type { Snippet, SnippetFormData, SnippetQueryParams } from '../types/snippets'

/** 获取片段列表 */
export async function fetchSnippets(params?: SnippetQueryParams): Promise<PaginatedResponse<Snippet>> {
  const { items, total, page, pageSize } = extractPaginated(
    await apiClient.get('/snippets', {
      params: { page: params?.page ?? 1, pageSize: params?.pageSize ?? 20, tag: params?.tags?.[0] },
    }) as any
  )

  let mapped: Snippet[] = items.map((item: any) => ({
    id: String(item.id), title: item.title, content: item.content, language: item.language,
    tags: item.tags ?? [], useCount: item.useCount ?? 0, createdAt: item.createdAt, updatedAt: item.updatedAt,
  }))

  if (params?.keyword) {
    const kw = params.keyword.toLowerCase()
    mapped = mapped.filter((s) =>
      s.title.toLowerCase().includes(kw) || s.content.toLowerCase().includes(kw) || s.tags.some((t) => t.toLowerCase().includes(kw))
    )
  }
  if (params?.tags && params.tags.length > 1) {
    mapped = mapped.filter((s) => params.tags!.some((tag) => s.tags.includes(tag)))
  }
  mapped.sort((a, b) => b.useCount - a.useCount)

  return { items: mapped, total, page, pageSize }
}

/** 创建片段 */
export async function createSnippet(data: SnippetFormData): Promise<Snippet> {
  const raw = extractData(await apiClient.post('/snippets', {
    title: data.title, content: data.content, language: data.language, tags: data.tags,
  })) as any
  return { ...raw, id: String(raw.id) }
}

/** 更新片段 */
export async function updateSnippet(id: string, data: SnippetFormData): Promise<Snippet> {
  const raw = extractData(await apiClient.put(`/snippets/${id}`, {
    title: data.title, content: data.content, language: data.language, tags: data.tags,
  })) as any
  return { ...raw, id: String(raw.id) }
}

/** 删除片段 */
export async function deleteSnippet(id: string): Promise<void> {
  await apiClient.delete(`/snippets/${id}`)
}

/** 记录使用 */
export async function recordSnippetUse(id: string): Promise<void> {
  await apiClient.post(`/snippets/${id}/use`)
}

/** 获取所有已用标签 */
export async function fetchAllTags(): Promise<string[]> {
  const items = extractData(await apiClient.get('/snippets', { params: { page: 1, pageSize: 100 } })) as any[]
  const tags = new Set<string>()
  items.forEach((s) => (s.tags ?? []).forEach((t: string) => tags.add(t)))
  return Array.from(tags).sort()
}
