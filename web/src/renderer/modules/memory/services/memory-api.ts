/**
 * 记忆 API 服务 — 对接后端 /api/v1/memory 真实接口
 */

import { apiClient, extractData, extractPaginated } from '@/services/api-client'
import type { MemoryEntry, MemoryListResponse, MemorySearchResult } from '../types/memory'

// ── 适配器：后端 → 前端类型 ─────────────────────────────────

interface BackendMemory {
  id: number
  conversationId?: number | null
  summary: string
  tags: string[]
  importance: number
  createdAt?: string
  updatedAt?: string
}

interface BackendSearchItem {
  id: number
  summary: string
  score: number
  tags: string[]
}

function adaptMemory(item: BackendMemory): MemoryEntry {
  return {
    id: String(item.id),
    summary: item.summary ?? '',
    content: item.summary ?? '',  // 后端 summary 即内容
    conversationId: item.conversationId ? String(item.conversationId) : '',
    tags: item.tags ?? [],
    createdAt: item.createdAt ?? new Date().toISOString(),
  }
}

function adaptSearchItem(item: BackendSearchItem): MemoryEntry {
  return {
    id: String(item.id),
    summary: item.summary ?? '',
    content: item.summary ?? '',
    conversationId: '',
    tags: item.tags ?? [],
    similarity: item.score ?? 0,
    createdAt: new Date().toISOString(),
  }
}

// ── 记忆列表 ────────────────────────────────────────────────

/** 获取记忆列表 */
export async function fetchMemories(
  params: { page?: number; pageSize?: number } = {}
): Promise<MemoryListResponse> {
  const { page = 1, pageSize = 20 } = params
  const { items, total } = extractPaginated(
    await apiClient.get('/memories', {
      params: { page, pageSize },
    }) as any
  )
  return {
    items: (items as BackendMemory[]).map(adaptMemory),
    total,
    page,
    pageSize,
  }
}

// ── 语义搜索 ────────────────────────────────────────────────

/** 语义搜索记忆 */
export async function searchMemories(query: string): Promise<MemorySearchResult> {
  if (!query.trim()) {
    return { items: [], query }
  }

  const data = extractData(
    await apiClient.get('/memories/search', {
      params: { q: query, limit: 10 },
    }) as any
  ) as { items?: BackendSearchItem[] } | null

  const items = (data?.items ?? []).map(adaptSearchItem)
  return { items, query }
}

// ── 删除记忆 ────────────────────────────────────────────────

/** 删除记忆 */
export async function deleteMemory(id: string): Promise<void> {
  await apiClient.delete(`/memories/${id}`)
}

// ── 创建记忆 ────────────────────────────────────────────────

/** 创建记忆 */
export async function createMemory(data: {
  summary: string
  tags?: string[]
  importance?: number
  conversationId?: number
}): Promise<MemoryEntry> {
  const raw = extractData(
    await apiClient.post('/memories', {
      summary: data.summary,
      tags: data.tags ?? [],
      importance: data.importance ?? 5,
      conversationId: data.conversationId,
    }) as any
  ) as BackendMemory
  return adaptMemory(raw)
}
