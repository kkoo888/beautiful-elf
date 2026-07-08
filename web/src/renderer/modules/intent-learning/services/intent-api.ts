import type { IntentCorrection, BehaviorPattern, SkillSuggestion, AnalyzeResult } from '../types/intent-learning'

const API_BASE = '/api/v1/intent-learning'

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  const json = await res.json()
  if (json.code && json.code !== 'SUCCESS') throw new Error(json.message || '请求失败')
  // 防御：后端返回 {code: 'SUCCESS', data: null} 时，调用方访问 res.data 不会出错
  return (json.data !== undefined ? json : { ...json, data: json.data ?? {} }) as T
}

// ── 纠正历史 ─────────────────────────────────────────────

export async function fetchCorrections(): Promise<IntentCorrection[]> {
  try {
    const res = await request<{ data: any[] }>(`${API_BASE}/corrections?page=1&pageSize=100`)
    return (res.data || []).map((item: any) => ({
      id: String(item.id),
      originalIntent: item.originalIntent || item.original_intent || '',
      correctModule: item.correctModule || item.correct_module || '',
      createdAt: item.createdAt || item.created_at || '',
    }))
  } catch {
    return []
  }
}

export async function createCorrection(originalIntent: string, correctModule: string): Promise<void> {
  await request(`${API_BASE}/corrections`, {
    method: 'POST',
    body: JSON.stringify({ originalIntent, correctModule }),
  })
}

// ── 行为模式 ─────────────────────────────────────────────

export async function fetchPatterns(): Promise<BehaviorPattern[]> {
  try {
    const res = await request<{ data: any[] }>(`${API_BASE}/patterns?page=1&pageSize=100`)
    return (res.data || []).map((item: any) => ({
      id: String(item.id),
      description: item.description || '',
      frequency: item.frequency || 0,
      actions: item.actions || [],
      isSolved: item.isSolved ?? item.is_solved ?? 0,
      createdAt: item.createdAt || item.created_at || '',
    }))
  } catch {
    return []
  }
}

// ── 技能建议 ─────────────────────────────────────────────

export async function fetchSuggestions(): Promise<SkillSuggestion[]> {
  try {
    const res = await request<{ data: any[] }>(`${API_BASE}/suggestions?page=1&pageSize=100&status=0`)
    return (res.data || []).map((item: any) => ({
      id: String(item.id),
      patternId: String(item.patternId || item.pattern_id || ''),
      name: item.name || '',
      description: item.description || '',
      ignoreCount: item.ignoreCount ?? item.ignore_count ?? 0,
      lastFeedback: item.lastFeedback || item.last_feedback || '',
      createdAt: item.createdAt || item.created_at || '',
    }))
  } catch {
    return []
  }
}

export async function acceptSuggestion(id: string): Promise<void> {
  await request(`${API_BASE}/suggestions/${id}/accept`, { method: 'POST' })
}

export async function ignoreSuggestion(id: string): Promise<void> {
  await request(`${API_BASE}/suggestions/${id}/ignore`, { method: 'POST' })
}

// ── 行为分析 ─────────────────────────────────────────────

export async function analyzeBehavior(): Promise<AnalyzeResult> {
  const res = await request<{ data: AnalyzeResult }>(`${API_BASE}/analyze`, { method: 'POST' })
  return res.data
}

export async function createIntentFromPattern(patternId: string): Promise<any> {
  const res = await request<{ data: any }>(`${API_BASE}/patterns/${patternId}/create-intent`, { method: 'POST' })
  return res.data
}
