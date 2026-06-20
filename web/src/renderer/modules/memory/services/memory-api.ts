/**
 * 记忆 API 服务 — 对接后端 /api/v1/markdown_memories 真实接口
 *
 * 新增提炼记忆 API（Hindsight 借鉴）:
 *   - distillMemories: 结构化提炼
 *   - listObservations: 列出提炼记忆
 *   - getObservation: 单条详情
 *   - updateObservation: 编辑
 *   - deleteObservation: 删除
 *   - getObservationStats: 分类统计
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
    content: item.summary ?? '',
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

export async function fetchMemories(
  params: { page?: number; pageSize?: number } = {}
): Promise<MemoryListResponse> {
  const { page = 1, pageSize = 20 } = params
  const { items, total } = extractPaginated(
    await apiClient.get('/memories', { params: { page, pageSize } }) as any
  )
  return { items: (items as BackendMemory[]).map(adaptMemory), total, page, pageSize }
}

export async function searchMemories(query: string): Promise<MemorySearchResult> {
  if (!query.trim()) return { items: [], query }
  const data = extractData(
    await apiClient.get('/memories/search', { params: { q: query, limit: 10 } }) as any
  ) as { items?: BackendSearchItem[] } | null
  const items = (data?.items ?? []).map(adaptSearchItem)
  return { items, query }
}

export async function deleteMemory(id: string): Promise<void> {
  await apiClient.delete(`/memories/${id}`)
}

export async function createMemory(data: {
  summary: string; tags?: string[]; importance?: number; conversationId?: number
}): Promise<MemoryEntry> {
  const raw = extractData(
    await apiClient.post('/memories', {
      summary: data.summary, tags: data.tags ?? [],
      importance: data.importance ?? 5, conversationId: data.conversationId,
    }) as any
  ) as BackendMemory
  return adaptMemory(raw)
}

// ── Markdown 记忆 API ──────────────────────────────────────

interface BackendMarkdownMemory {
  id: number; userId?: number; title: string; content: string
  memoryType?: string; wordCount?: number; qdrantSynced?: number
}

interface BackendMarkdownListItem {
  id: number; title: string; memoryType?: string
  wordCount?: number; createdAt?: string; updatedAt?: string
}

export interface MarkdownMemoryEntry {
  id: string; title: string; content: string; memoryType: string
  wordCount: number; createdAt?: string; updatedAt?: string
}

function adaptMarkdownMemory(item: BackendMarkdownMemory): MarkdownMemoryEntry {
  return {
    id: String(item.id), title: item.title ?? '', content: item.content ?? '',
    memoryType: item.memoryType ?? 'daily', wordCount: item.wordCount ?? 0,
  }
}

function adaptMarkdownListItem(item: BackendMarkdownListItem): MarkdownMemoryEntry {
  return {
    id: String(item.id), title: item.title ?? '', content: '',
    memoryType: item.memoryType ?? 'daily', wordCount: item.wordCount ?? 0,
    createdAt: item.createdAt ?? undefined, updatedAt: item.updatedAt ?? undefined,
  }
}

export async function fetchDailyLogs(limit = 7): Promise<MarkdownMemoryEntry[]> {
  const { items } = extractPaginated(
    await apiClient.get('/markdown_memories/daily/list', { params: { limit } }) as any
  )
  return (items as BackendMarkdownListItem[]).map(adaptMarkdownListItem)
}

export async function fetchDailyLog(date: string): Promise<MarkdownMemoryEntry | null> {
  const data = extractData(
    await apiClient.get('/markdown_memories', { params: { memoryType: 'daily' } }) as any
  )
  if (!data) return null
  const items = Array.isArray(data) ? data : (data as any).items ?? []
  const found = (items as BackendMarkdownMemory[]).find(i => i.title === date)
  return found ? adaptMarkdownMemory(found) : null
}

export async function fetchMarkdownMemory(id: string): Promise<MarkdownMemoryEntry> {
  const raw = extractData(
    await apiClient.get(`/markdown_memories/${id}`) as any
  ) as BackendMarkdownMemory
  return adaptMarkdownMemory(raw)
}

export async function fetchLongTermMemory(): Promise<MarkdownMemoryEntry> {
  const raw = extractData(
    await apiClient.get('/markdown_memories/longterm') as any
  ) as BackendMarkdownMemory
  return adaptMarkdownMemory(raw)
}

export async function updateLongTermMemory(content: string): Promise<MarkdownMemoryEntry> {
  const raw = extractData(
    await apiClient.put('/markdown_memories/longterm', {
      title: 'MEMORY', content, memoryType: 'longterm',
    }) as any
  ) as BackendMarkdownMemory
  return adaptMarkdownMemory(raw)
}

// ── 提炼记忆 API（Hindsight 借鉴）──────────────────────────

export interface DistillRequest {
  days: number
  mission: string
  directives: string[]
  categories: string[]
}

export interface ObservationSource {
  sourceId: number
  logId: number
  logTitle: string
  evidenceQuote: string
}

export interface Observation {
  id: number
  content: string
  category: string
  freshness: string
  sourceDays: number
  proofCount: number
  sources: ObservationSource[]
  createdAt?: string
  updatedAt?: string
}

export interface DistillResult {
  observations: Observation[]
  sourceDays: number
  sourceLogs: string[]
  totalCount: number
}

/** 提炼记忆（结构化提取，写入 observation 表） */
export async function distillMemories(request: DistillRequest): Promise<DistillResult> {
  return extractData(
    await apiClient.post('/markdown_memories/distill', request) as any
  ) as DistillResult
}

/** 获取提炼记忆列表 */
export async function listObservations(params: {
  page?: number; pageSize?: number; category?: string
} = {}): Promise<{ items: Observation[]; total: number }> {
  const { page = 1, pageSize = 50, category } = params
  const { items, total } = extractPaginated(
    await apiClient.get('/markdown_memories/observations', {
      params: { page, pageSize, category },
    }) as any
  )
  return { items: items as Observation[], total }
}

/** 获取单条提炼记忆详情 */
export async function getObservation(id: number): Promise<Observation> {
  return extractData(
    await apiClient.get(`/markdown_memories/observations/${id}`) as any
  ) as Observation
}

/** 编辑单条提炼记忆 */
export async function updateObservation(
  id: number, data: { content?: string; category?: string; freshness?: string }
): Promise<Observation> {
  return extractData(
    await apiClient.put(`/markdown_memories/observations/${id}`, data) as any
  ) as Observation
}

/** 删除单条提炼记忆 */
export async function deleteObservation(id: number): Promise<void> {
  await apiClient.delete(`/markdown_memories/observations/${id}`)
}

/** 获取分类统计 */
export async function getObservationStats(): Promise<Record<string, number>> {
  return extractData(
    await apiClient.get('/markdown_memories/observations/stats') as any
  ) as Record<string, number>
}

/** 创建 observation 与 daily log 的关联 */
export async function createObservationSource(
  observationId: number, sourceMemoryId: number, evidenceQuote = ''
): Promise<{ id: number }> {
  return extractData(
    await apiClient.post(
      `/markdown_memories/observations/${observationId}/sources?sourceMemoryId=${sourceMemoryId}&evidenceQuote=${encodeURIComponent(evidenceQuote)}`
    ) as any
  ) as { id: number }
}

/** 删除关联记录 */
export async function deleteObservationSource(sourceId: number): Promise<void> {
  await apiClient.delete(`/markdown_memories/sources/${sourceId}`)
}

/** 重新评分记忆重要性（LLM 精确评分） */
export async function rescoreMemories(params: {
  pointIds?: string[]
  userId?: number
}): Promise<{ rescored: number; updated: number }> {
  return extractData(
    await apiClient.post('/memories/rescore', {
      point_ids: params.pointIds || [],
      user_id: params.userId || 0,
    }) as any
  ) as { rescored: number; updated: number }
}
