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
 * 执行专家团 — WebSocket 流式返回
 * 通过已有的 WS 持久连接发送，逐事件回调
 */
export async function executeExpertTeam(
  teamId: number,
  input: ExpertTeamExecuteInput,
  onEvent: (event: ExpertTeamSSEEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  return new Promise<void>((resolve, reject) => {
    const token = localStorage.getItem('beautiful-elf:auth_token')
    const base = (apiClient.defaults.baseURL || '').replace(/^http/, 'ws').replace(/\/+$/, '')
    const url = `${base}/api/v1/ws/chat?token=${token || ''}`

    const ws = new WebSocket(url)
    let settled = false

    const cleanup = () => {
      ws.removeEventListener('message', handleMessage)
      ws.removeEventListener('close', handleClose)
      ws.removeEventListener('error', handleError)
      if (signal) signal.removeEventListener('abort', handleAbort)
    }

    const handleMessage = (event: MessageEvent) => {
      if (settled) return
      try {
        const data = JSON.parse(event.data)
        // 心跳
        if (data.type === 'ping') {
          ws.send(JSON.stringify({ type: 'pong' }))
          return
        }
        // 专家团事件（后端直接透传 dict，字段在顶层）
        if (data.type && data.type !== 'pong') {
          onEvent(data as ExpertTeamSSEEvent)
        }
        // done/error 结束
        if (data.type === 'done' || data.type === 'error') {
          settled = true
          cleanup()
          if (data.type === 'error') {
            reject(new Error(data.message || '专家团执行失败'))
          } else {
            resolve()
          }
        }
      } catch { /* skip malformed */ }
    }

    const handleClose = () => {
      if (!settled) {
        settled = true
        cleanup()
        reject(new Error('WebSocket 连接断开'))
      }
    }

    const handleError = () => {
      if (!settled) {
        settled = true
        cleanup()
        reject(new Error('WebSocket 连接失败'))
      }
    }

    const handleAbort = () => {
      if (!settled) {
        settled = true
        cleanup()
        ws.close()
        reject(new DOMException('Aborted', 'AbortError'))
      }
    }

    ws.addEventListener('message', handleMessage)
    ws.addEventListener('close', handleClose)
    ws.addEventListener('error', handleError)
    if (signal) signal.addEventListener('abort', handleAbort)

    ws.addEventListener('open', () => {
      ws.send(JSON.stringify({
        type: 'expert_team_execute',
        teamId,
        inputText: input.inputText,
        maxRounds: input.maxRounds ?? null,
      }))
    })
  })
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
