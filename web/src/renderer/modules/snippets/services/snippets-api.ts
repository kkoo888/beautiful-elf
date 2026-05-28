import { apiClient } from '@/services/api-client'
import type { ApiResponse, PaginatedResponse } from '@/types'
import type { Snippet, SnippetFormData, SnippetQueryParams } from '../types/snippets'

/** Mock 数据 */
const MOCK_SNIPPETS: Snippet[] = [
  {
    id: '1',
    title: 'React useState Hook',
    content: `import { useState } from 'react';\n\nfunction Counter() {\n  const [count, setCount] = useState(0);\n  return (\n    <button onClick={() => setCount(c => c + 1)}>\n      Count: {count}\n    </button>\n  );\n}`,
    language: 'typescript',
    tags: ['react', 'hooks'],
    useCount: 42,
    createdAt: '2026-05-01T10:00:00Z',
    updatedAt: '2026-05-20T14:30:00Z',
  },
  {
    id: '2',
    title: 'Python 快速排序',
    content: `def quicksort(arr):\n    if len(arr) <= 1:\n        return arr\n    pivot = arr[len(arr) // 2]\n    left = [x for x in arr if x < pivot]\n    middle = [x for x in arr if x == pivot]\n    right = [x for x in arr if x > pivot]\n    return quicksort(left) + middle + quicksort(right)`,
    language: 'python',
    tags: ['algorithm', 'sort'],
    useCount: 28,
    createdAt: '2026-04-15T08:00:00Z',
    updatedAt: '2026-05-10T09:00:00Z',
  },
  {
    id: '3',
    title: 'CSS Flexbox 居中',
    content: `.container {\n  display: flex;\n  justify-content: center;\n  align-items: center;\n  min-height: 100vh;\n}`,
    language: 'css',
    tags: ['css', 'layout'],
    useCount: 35,
    createdAt: '2026-03-20T12:00:00Z',
    updatedAt: '2026-05-18T16:00:00Z',
  },
  {
    id: '4',
    title: 'Fetch API 封装',
    content: `async function request<T>(url: string, options?: RequestInit): Promise<T> {\n  const res = await fetch(url, {\n    headers: { 'Content-Type': 'application/json' },\n    ...options,\n  });\n  if (!res.ok) throw new Error(res.statusText);\n  return res.json();\n}`,
    language: 'typescript',
    tags: ['http', 'fetch', 'utils'],
    useCount: 19,
    createdAt: '2026-04-01T15:00:00Z',
    updatedAt: '2026-05-15T11:00:00Z',
  },
  {
    id: '5',
    title: 'Shell 文件批量重命名',
    content: '#!/bin/bash\nfor f in *.txt; do\n  mv "$f" "${f%.txt}.md"\ndone',
    language: 'shell',
    tags: ['shell', 'batch'],
    useCount: 12,
    createdAt: '2026-05-05T10:00:00Z',
    updatedAt: '2026-05-22T08:00:00Z',
  },
]

/** 模拟延迟 */
const delay = (ms = 300) => new Promise((r) => setTimeout(r, ms))

/** 获取片段列表（支持搜索、标签筛选、分页） */
export async function fetchSnippets(
  params?: SnippetQueryParams
): Promise<PaginatedResponse<Snippet>> {
  // 实际请求：
  // const { data } = await apiClient.get<ApiResponse<PaginatedResponse<Snippet>>>('/snippets', { params })
  // return data.data

  await delay()
  let items = [...MOCK_SNIPPETS]

  // 搜索过滤
  if (params?.keyword) {
    const kw = params.keyword.toLowerCase()
    items = items.filter(
      (s) =>
        s.title.toLowerCase().includes(kw) ||
        s.content.toLowerCase().includes(kw) ||
        s.tags.some((t) => t.toLowerCase().includes(kw))
    )
  }

  // 标签过滤
  if (params?.tags && params.tags.length > 0) {
    items = items.filter((s) => params.tags!.some((tag) => s.tags.includes(tag)))
  }

  // 按使用次数排序（高频靠前）
  items.sort((a, b) => b.useCount - a.useCount)

  const page = params?.page ?? 1
  const pageSize = params?.pageSize ?? 20
  const total = items.length
  const start = (page - 1) * pageSize
  items = items.slice(start, start + pageSize)

  return { items, total, page, pageSize }
}

/** 创建片段 */
export async function createSnippet(data: SnippetFormData): Promise<Snippet> {
  // const { data: res } = await apiClient.post<ApiResponse<Snippet>>('/snippets', data)
  // return res.data

  await delay()
  const now = new Date().toISOString()
  const snippet: Snippet = {
    id: crypto.randomUUID(),
    ...data,
    useCount: 0,
    createdAt: now,
    updatedAt: now,
  }
  MOCK_SNIPPETS.unshift(snippet)
  return snippet
}

/** 更新片段 */
export async function updateSnippet(id: string, data: SnippetFormData): Promise<Snippet> {
  // const { data: res } = await apiClient.put<ApiResponse<Snippet>>(`/snippets/${id}`, data)
  // return res.data

  await delay()
  const idx = MOCK_SNIPPETS.findIndex((s) => s.id === id)
  if (idx === -1) throw new Error('Snippet not found')
  MOCK_SNIPPETS[idx] = {
    ...MOCK_SNIPPETS[idx],
    ...data,
    updatedAt: new Date().toISOString(),
  }
  return MOCK_SNIPPETS[idx]
}

/** 删除片段 */
export async function deleteSnippet(id: string): Promise<void> {
  // await apiClient.delete(`/snippets/${id}`)

  await delay()
  const idx = MOCK_SNIPPETS.findIndex((s) => s.id === id)
  if (idx !== -1) MOCK_SNIPPETS.splice(idx, 1)
}

/** 记录使用 */
export async function recordSnippetUse(id: string): Promise<void> {
  // await apiClient.post(`/snippets/${id}/use`)

  await delay(100)
  const snippet = MOCK_SNIPPETS.find((s) => s.id === id)
  if (snippet) snippet.useCount += 1
}

/** 获取所有已用标签 */
export async function fetchAllTags(): Promise<string[]> {
  await delay(100)
  const tags = new Set<string>()
  MOCK_SNIPPETS.forEach((s) => s.tags.forEach((t) => tags.add(t)))
  return Array.from(tags).sort()
}
