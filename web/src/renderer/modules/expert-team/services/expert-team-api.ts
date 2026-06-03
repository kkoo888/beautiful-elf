/**
 * 专家团工作流 API 服务
 *
 * 后端 Query 参数: page, page_size, status → snake_case
 */

import { apiClient, extractData, extractPaginated } from '@/services/api-client'
import type {
  ExpertTeam, ExpertTeamFormInput, ExpertTeamUpdateInput,
  ExpertMember, ExpertMemberFormInput,
  ExpertTeamRun, ExpertTeamExecuteInput, ExpertTeamExecuteResult,
} from '../types'

/** 适配后端成员 → 前端类型 */
function adaptMember(raw: any): ExpertMember {
  return {
    id: raw.id,
    teamId: raw.teamId,
    name: raw.memberName ?? raw.name ?? '',
    role: raw.memberRole ?? raw.role ?? '',
    avatar: raw.avatar ?? '🤖',
    systemPrompt: raw.systemPrompt ?? '',
    modelName: raw.modelName ?? '',
    temperature: raw.temperature ?? 70,
    maxTokens: raw.maxTokens ?? 2048,
    toolsJson: raw.toolsJson ?? null,
    sortOrder: raw.sortOrder ?? 0,
    enabled: raw.isEnabled ?? raw.enabled ?? 1,
    createdAt: raw.createdAt ?? null,
    updatedAt: raw.updatedAt ?? null,
  }
}

/** 适配后端专家团 → 前端类型 */
function adaptTeam(raw: any): ExpertTeam {
  return {
    id: raw.id,
    name: raw.teamName ?? raw.name ?? '',
    description: raw.description ?? '',
    icon: raw.icon ?? '👥',
    category: raw.category ?? '通用',
    orchestratorPrompt: raw.orchestratorPrompt ?? '',
    synthesizerPrompt: raw.synthesizerPrompt ?? '',
    maxRounds: raw.maxRounds ?? 3,
    enabled: raw.isEnabled ?? raw.enabled ?? 1,
    version: raw.version ?? 1,
    configJson: raw.configJson ?? null,
    members: (raw.members ?? []).map(adaptMember),
    createdAt: raw.createdAt ?? null,
    updatedAt: raw.updatedAt ?? null,
  }
}

export async function fetchExpertTeams(params?: {
  category?: string; enabled?: number; page?: number; pageSize?: number
}): Promise<{ items: ExpertTeam[]; total: number }> {
  const { items, total } = extractPaginated(await apiClient.get('/expert_teams', {
    params: { category: params?.category, enabled: params?.enabled, page: params?.page, pageSize: params?.pageSize },
  }) as any)
  return { items: items.map(adaptTeam), total }
}

export async function fetchExpertTeamById(id: number): Promise<ExpertTeam> {
  return adaptTeam(extractData(await apiClient.get(`/expert_teams/${id}`)))
}

/** 前端表单 → 后端请求体 */
function toBackendTeam(input: ExpertTeamFormInput | ExpertTeamUpdateInput): Record<string, any> {
  const body: Record<string, any> = {}
  if (input.name !== undefined) body.team_name = input.name
  if (input.description !== undefined) body.description = input.description
  if (input.icon !== undefined) body.icon = input.icon
  if (input.category !== undefined) body.category = input.category
  if (input.orchestratorPrompt !== undefined) body.orchestrator_prompt = input.orchestratorPrompt
  if (input.synthesizerPrompt !== undefined) body.synthesizer_prompt = input.synthesizerPrompt
  if (input.maxRounds !== undefined) body.max_rounds = input.maxRounds
  if ('members' in input && input.members) {
    body.members = input.members.map((m) => ({
      member_name: m.name,
      member_role: m.role,
      avatar: m.avatar ?? '🤖',
      system_prompt: m.systemPrompt,
      model_name: m.modelName ?? '',
      temperature: m.temperature ?? 70,
      max_tokens: m.maxTokens ?? 2048,
      is_enabled: m.enabled ?? 1,
    }))
  }
  return body
}

export async function createExpertTeam(input: ExpertTeamFormInput): Promise<ExpertTeam> {
  return adaptTeam(extractData(await apiClient.post('/expert_teams', toBackendTeam(input))))
}

export async function updateExpertTeam(id: number, input: ExpertTeamUpdateInput): Promise<ExpertTeam> {
  return adaptTeam(extractData(await apiClient.put(`/expert_teams/${id}`, toBackendTeam(input))))
}

export async function deleteExpertTeam(id: number): Promise<void> {
  await apiClient.delete(`/expert_teams/${id}`)
}

export async function addExpertMember(teamId: number, input: ExpertMemberFormInput): Promise<ExpertMemberFormInput> {
  return extractData(await apiClient.post(`/expert_teams/${teamId}/members`, input))
}

export async function updateExpertMember(memberId: number, input: Partial<ExpertMemberFormInput>): Promise<ExpertMemberFormInput> {
  return extractData(await apiClient.put(`/expert_teams/members/${memberId}`, input))
}

export async function deleteExpertMember(memberId: number): Promise<void> {
  await apiClient.delete(`/expert_teams/members/${memberId}`)
}

export async function executeExpertTeam(teamId: number, input: ExpertTeamExecuteInput): Promise<ExpertTeamExecuteResult> {
  return extractData(await apiClient.post(`/expert_teams/${teamId}/execute`, input))
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
