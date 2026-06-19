/**
 * 专家团工作流 API 服务
 *
 * 后端 Query 参数: page, page_size, status → snake_case
 */

import { apiClient, extractData, extractPaginated } from '@/services/api-client'
import type {
  ExpertTeam, ExpertTeamFormInput, ExpertTeamUpdateInput, ExpertTeamBindExperts,
  Expert, ExpertFormInput,
  ExpertSkill, ExpertSkillCreate, ExpertSkillUpdate,
  ExpertTeamRun, ExpertTeamExecuteInput, ExpertTeamExecuteResult,
} from '../types'

// ─── 专家 CRUD（独立实体）─────────────────────────────────

export async function fetchExperts(params?: {
  enabled?: number; page?: number; pageSize?: number
}): Promise<{ items: Expert[]; total: number }> {
  const { items, total } = extractPaginated(await apiClient.get('/expert_teams/experts', {
    params: { enabled: params?.enabled, page: params?.page, pageSize: params?.pageSize },
  }) as any)
  return { items, total }
}

export async function fetchExpertById(id: number): Promise<Expert> {
  return extractData(await apiClient.get(`/expert_teams/experts/${id}`))
}

export async function createExpert(input: ExpertFormInput): Promise<Expert> {
  return extractData(await apiClient.post('/expert_teams/experts', input))
}

export async function updateExpert(id: number, input: Partial<ExpertFormInput>): Promise<Expert> {
  return extractData(await apiClient.put(`/expert_teams/experts/${id}`, input))
}

export async function deleteExpert(id: number): Promise<void> {
  await apiClient.delete(`/expert_teams/experts/${id}`)
}

// ─── 专家技能绑定 ────────────────────────────────────────

export async function fetchExpertSkills(expertId: number): Promise<ExpertSkill[]> {
  return extractData(await apiClient.get(`/expert_teams/experts/${expertId}/skills`))
}

export async function bindExpertSkill(expertId: number, input: ExpertSkillCreate): Promise<ExpertSkill> {
  return extractData(await apiClient.post(`/expert_teams/experts/${expertId}/skills`, input))
}

export async function updateExpertSkillBind(bindId: number, input: ExpertSkillUpdate): Promise<ExpertSkill> {
  return extractData(await apiClient.put(`/expert_teams/expert-skills/${bindId}`, input))
}

export async function unbindExpertSkill(bindId: number): Promise<void> {
  await apiClient.delete(`/expert_teams/expert-skills/${bindId}`)
}

// ─── 专家团 CRUD ─────────────────────────────────────────

export async function fetchExpertTeams(params?: {
  category?: string; enabled?: number; page?: number; pageSize?: number
}): Promise<{ items: ExpertTeam[]; total: number }> {
  const { items, total } = extractPaginated(await apiClient.get('/expert_teams', {
    params: { category: params?.category, enabled: params?.enabled, page: params?.page, pageSize: params?.pageSize },
  }) as any)
  return { items, total }
}

export async function fetchExpertTeamById(id: number): Promise<ExpertTeam> {
  return extractData(await apiClient.get(`/expert_teams/${id}`))
}

export async function createExpertTeam(input: ExpertTeamFormInput): Promise<ExpertTeam> {
  return extractData(await apiClient.post('/expert_teams', input))
}

export async function updateExpertTeam(id: number, input: ExpertTeamUpdateInput): Promise<ExpertTeam> {
  return extractData(await apiClient.put(`/expert_teams/${id}`, input))
}

export async function deleteExpertTeam(id: number): Promise<void> {
  await apiClient.delete(`/expert_teams/${id}`)
}

// ─── 专家团绑定专家 ──────────────────────────────────────

export async function bindExpertsToTeam(teamId: number, data: ExpertTeamBindExperts): Promise<ExpertTeam> {
  return extractData(await apiClient.post(`/expert_teams/${teamId}/bind-experts`, data))
}

// ─── 执行与运行记录 ─────────────────────────────────────

export interface ExpertTeamSSEEvent {
  type: string
  expertName?: string
  expertRole?: string
  avatar?: string
  content?: string
  subtask?: string
  durationMs?: number
  runId?: number
  round?: number
  message?: string
  status?: string
  output?: string
}

/**
 * 执行专家团 — SSE 流式返回
 * 后端返回 text/event-stream，前端逐事件处理
 */
export async function executeExpertTeam(
  teamId: number,
  input: ExpertTeamExecuteInput,
  onEvent: (event: ExpertTeamSSEEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const token = localStorage.getItem('beautiful-elf:auth_token')
  const base = (apiClient.defaults.baseURL || '').replace(/\/+$/, '')
  const url = `${base}/expert_teams/${teamId}/execute`

  const res = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(input),
    signal,
  })

  if (!res.ok) {
    throw new Error(`专家团执行失败: ${res.status} ${res.statusText}`)
  }

  const reader = res.body?.getReader()
  if (!reader) throw new Error('无法读取 SSE 流')

  const decoder = new TextDecoder()
  let buffer = ''

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        try {
          const event = JSON.parse(line.slice(6)) as ExpertTeamSSEEvent
          onEvent(event)
        } catch {
          // 心跳行或无效 JSON，跳过
        }
      }
    }
  } finally {
    reader.releaseLock()
  }
}

export async function fetchExpertTeamRuns(
  teamId: number, params?: { page?: number; pageSize?: number }
): Promise<{ items: ExpertTeamRun[]; total: number }> {
  const { items, total } = extractPaginated(await apiClient.get(`/expert_teams/${teamId}/runs`, {
    params: { page: params?.page, pageSize: params?.pageSize },
  }) as any)
  return { items, total }
}

export async function fetchAllExpertRuns(params?: {
  status?: number; page?: number; pageSize?: number
}): Promise<{ items: ExpertTeamRun[]; total: number }> {
  const { items, total } = extractPaginated(await apiClient.get('/expert_teams/runs/all', {
    params: { status: params?.status, page: params?.page, pageSize: params?.pageSize },
  }) as any)
  return { items, total }
}

export async function fetchExpertRunById(runId: number): Promise<ExpertTeamRun> {
  return extractData(await apiClient.get(`/expert_teams/runs/${runId}`))
}

// ─── 工具接口 ─────────────────────────────────────────────

export async function polishPrompt(content: string): Promise<string> {
  return extractData(await apiClient.post('/expert_teams/polish-prompt', { content }))
}
