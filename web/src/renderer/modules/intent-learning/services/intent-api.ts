import { apiClient, extractData, extractPaginated } from '@/services/api-client'
import type { IntentCorrection, BehaviorPattern, SkillSuggestion, AnalyzeResult } from '../types/intent-learning'

const BASE = '/intent-learning'

// ── 纠正历史 ─────────────────────────────────────────────

export async function fetchCorrections(): Promise<IntentCorrection[]> {
  try {
    const { items } = await extractPaginated<Record<string, unknown>>(
      await apiClient.get(`${BASE}/corrections`, { params: { page: 1, pageSize: 100 } })
    )
    return items.map((item) => ({
      id: String(item.id),
      originalIntent: (item.originalIntent as string) || '',
      correctModule: (item.correctModule as string) || '',
      createdAt: (item.createdAt as string) || '',
    }))
  } catch {
    return []
  }
}

export async function createCorrection(originalIntent: string, correctModule: string): Promise<void> {
  await apiClient.post(`${BASE}/corrections`, { originalIntent, correctModule })
}

// ── 行为模式 ─────────────────────────────────────────────

export async function fetchPatterns(): Promise<BehaviorPattern[]> {
  try {
    const { items } = await extractPaginated<Record<string, unknown>>(
      await apiClient.get(`${BASE}/patterns`, { params: { page: 1, pageSize: 100 } })
    )
    return items.map((item) => ({
      id: String(item.id),
      description: (item.description as string) || '',
      frequency: (item.frequency as number) || 0,
      actions: (item.actions as string[]) || [],
      isSolved: (item.isSolved as number) ?? 0,
      createdAt: (item.createdAt as string) || '',
    }))
  } catch {
    return []
  }
}

// ── 技能建议 ─────────────────────────────────────────────

export async function fetchSuggestions(): Promise<SkillSuggestion[]> {
  try {
    const { items } = await extractPaginated<Record<string, unknown>>(
      await apiClient.get(`${BASE}/suggestions`, { params: { page: 1, pageSize: 100, status: 0 } })
    )
    return items.map((item) => ({
      id: String(item.id),
      patternId: String(item.patternId || ''),
      name: (item.name as string) || '',
      description: (item.description as string) || '',
      ignoreCount: (item.ignoreCount as number) ?? 0,
      lastFeedback: (item.lastFeedback as string) || '',
      createdAt: (item.createdAt as string) || '',
    }))
  } catch {
    return []
  }
}

export async function acceptSuggestion(id: string): Promise<void> {
  await apiClient.post(`${BASE}/suggestions/${id}/accept`)
}

export async function ignoreSuggestion(id: string): Promise<void> {
  await apiClient.post(`${BASE}/suggestions/${id}/ignore`)
}

// ── 行为分析 ─────────────────────────────────────────────

export async function analyzeBehavior(): Promise<AnalyzeResult> {
  const res = await apiClient.post(`${BASE}/analyze`)
  return extractData(res) as unknown as AnalyzeResult
}

export async function createIntentFromPattern(patternId: string): Promise<unknown> {
  const res = await apiClient.post(`${BASE}/patterns/${patternId}/create-intent`)
  return extractData(res)
}
