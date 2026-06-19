/**
 * 实体记忆 API — 借鉴 Hindsight TEMPR + CARA + Reflect
 *
 * 新增 API:
 *   - 实体 CRUD（entities）
 *   - 关系 CRUD（relations）
 *   - 图谱数据（graph）
 *   - 洞察 CRUD（insights）
 *   - 反思触发（reflect）
 */

import { apiClient, extractData, extractPaginated } from '@/services/api-client'
import type { MemoryEpisode, MemoryInsightHistory, OptimizationResult, MemoryEntry } from '../types/memory'

// ── 类型定义 ──────────────────────────────────────────────

export interface MemoryEntity {
  id: number
  name: string
  entityType: 'person' | 'tech' | 'project' | 'tool' | 'concept' | 'org'
  description: string
  aliases: string
  mentionCount: number
  lastMentionedAt: string
  createdAt?: string
}

export interface EntityRelation {
  id: number
  sourceEntityId: number
  targetEntityId: number
  relationType: 'uses' | 'depends' | 'belongs' | 'creates' | 'works_at' | 'related'
  weight: number
  evidence: string
  sourceObsId: number
}

export interface EntityGraphData {
  nodes: Array<{
    id: string
    name: string
    type: string
    description: string
    mentionCount: number
  }>
  edges: Array<{
    id: string
    source: string
    target: string
    type: string
    weight: number
  }>
}

export interface MemoryInsight {
  id: number
  content: string
  insightType: 'pattern' | 'trend' | 'risk' | 'insight'
  confidence: number
  evidenceCount: number
  sourcePeriod: string
  status: 'active' | 'superseded' | 'dismissed'
  createdAt?: string
}

export interface ReflectResult {
  insights: MemoryInsight[]
  analyzed: number
  categoryBreakdown: Record<string, number>
  freshnessBreakdown: Record<string, number>
}

// ── 实体 API ──────────────────────────────────────────────

export async function listEntities(params?: {
  page?: number; pageSize?: number; entityType?: string; keyword?: string
}): Promise<{ items: MemoryEntity[]; total: number }> {
  const { items, total } = extractPaginated(
    await apiClient.get('/memory/entities', { params }) as any
  )
  return { items: items as MemoryEntity[], total }
}

export async function createEntity(data: {
  name: string; entityType?: string; description?: string; aliases?: string
}): Promise<MemoryEntity> {
  return extractData(await apiClient.post('/memory/entities', data) as any) as MemoryEntity
}

export async function updateEntity(id: number, data: {
  name?: string; entityType?: string; description?: string; aliases?: string
}): Promise<MemoryEntity> {
  return extractData(await apiClient.put(`/memory/entities/${id}`, data) as any) as MemoryEntity
}

export async function deleteEntity(id: number): Promise<void> {
  await apiClient.delete(`/memory/entities/${id}`)
}

// ── 关系 API ──────────────────────────────────────────────

export async function listRelations(entityId?: number): Promise<EntityRelation[]> {
  return extractData(
    await apiClient.get('/memory/entities/relations', { params: { entityId } }) as any
  ) as EntityRelation[]
}

export async function createRelation(data: {
  sourceEntityId: number; targetEntityId: number
  relationType?: string; evidence?: string; sourceObsId?: number
}): Promise<EntityRelation> {
  return extractData(await apiClient.post('/memory/entities/relations', data) as any) as EntityRelation
}

export async function deleteRelation(id: number): Promise<void> {
  await apiClient.delete(`/memory/entities/relations/${id}`)
}

// ── 图谱 API ──────────────────────────────────────────────

export async function getEntityGraph(): Promise<EntityGraphData> {
  return extractData(
    await apiClient.get('/memory/entities/graph') as any
  ) as EntityGraphData
}

// ── 洞察 API ──────────────────────────────────────────────

export async function listInsights(params?: {
  page?: number; pageSize?: number; type?: string; status?: string
}): Promise<{ items: MemoryInsight[]; total: number }> {
  const { items, total } = extractPaginated(
    await apiClient.get('/memory/insights', { params }) as any
  )
  return { items: items as MemoryInsight[], total }
}

export async function createInsight(data: {
  content: string; insightType?: string; confidence?: number; sourcePeriod?: string
}): Promise<MemoryInsight> {
  return extractData(await apiClient.post('/memory/insights', data) as any) as MemoryInsight
}

export async function updateInsight(id: number, data: {
  content?: string; confidence?: number; status?: string
}): Promise<MemoryInsight> {
  return extractData(await apiClient.put(`/memory/insights/${id}`, data) as any) as MemoryInsight
}

export async function deleteInsight(id: number): Promise<void> {
  await apiClient.delete(`/memory/insights/${id}`)
}

// ── 反思 API ──────────────────────────────────────────────

export async function triggerReflect(days = 7): Promise<ReflectResult> {
  return extractData(
    await apiClient.post('/memory/reflect', { days }) as any
  ) as ReflectResult
}

// ── Episode API ──────────────────────────────────────────────

export async function listEpisodes(params?: {
  entity_id?: number; start_time?: string; end_time?: string
}): Promise<MemoryEpisode[]> {
  return extractData(
    await apiClient.get('/memory/episodes', { params }) as any
  ) as MemoryEpisode[]
}

export async function getEpisode(id: number): Promise<MemoryEpisode> {
  return extractData(
    await apiClient.get(`/memory/episodes/${id}`) as any
  ) as MemoryEpisode
}

export async function createEpisode(data: {
  conversation_id: number; title: string; summary: string
}): Promise<MemoryEpisode> {
  return extractData(
    await apiClient.post('/memory/episodes', data) as any
  ) as MemoryEpisode
}

export async function searchEpisodes(q: string): Promise<MemoryEpisode[]> {
  return extractData(
    await apiClient.get('/memory/episodes/search', { params: { q } }) as any
  ) as MemoryEpisode[]
}

// ── Insight History API ──────────────────────────────────────────────

export async function getInsightHistory(insight_id: number): Promise<MemoryInsightHistory[]> {
  return extractData(
    await apiClient.get(`/memory/insights/${insight_id}/history`) as any
  ) as MemoryInsightHistory[]
}

export async function getConflicts(): Promise<MemoryInsight[]> {
  return extractData(
    await apiClient.get('/memory/insights/conflicts') as any
  ) as MemoryInsight[]
}

export async function arbitrateInsight(insight_id: number, data: {
  importance?: number
}): Promise<MemoryInsight> {
  return extractData(
    await apiClient.post(`/memory/insights/${insight_id}/arbitrate`, data) as any
  ) as MemoryInsight
}

// ── Optimization API ──────────────────────────────────────────────

export async function getOptimizedMemories(params: {
  rerank?: boolean; decay?: boolean
}): Promise<MemoryEntry[]> {
  return extractData(
    await apiClient.get('/memories/optimize', { params }) as any
  ) as MemoryEntry[]
}

export async function triggerOptimization(data: {
  importance_boost?: number
}): Promise<OptimizationResult> {
  return extractData(
    await apiClient.post('/memories/optimize', data) as any
  ) as OptimizationResult
}
