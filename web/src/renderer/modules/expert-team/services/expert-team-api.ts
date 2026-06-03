/**
 * 专家团工作流 API 服务
 *
 * 统一使用 extractData / extractPaginated，消除 data.data 嵌套。
 */

import { apiClient, extractData, extractPaginated } from '@/services/api-client'
import type {
  ExpertTeam, ExpertTeamFormInput, ExpertTeamUpdateInput,
  ExpertMemberFormInput, ExpertTeamRun, ExpertTeamExecuteInput, ExpertTeamExecuteResult,
} from '../types'

// ─── 专家团 CRUD ─────────────────────────────────────────

export async function fetchExpertTeams(params?: {
  category?: string; enabled?: number; page?: number; pageSize?: number
}): Promise<{ items: ExpertTeam[]; total: number }> {
  const { items, total } = extractPaginated(await apiClient.get('/expert_teams', { params }) as any)
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

// ─── 专家成员 ────────────────────────────────────────────

export async function addExpertMember(teamId: number, input: ExpertMemberFormInput): Promise<ExpertMemberFormInput> {
  return extractData(await apiClient.post(`/expert_teams/${teamId}/members`, input))
}

export async function updateExpertMember(memberId: number, input: Partial<ExpertMemberFormInput>): Promise<ExpertMemberFormInput> {
  return extractData(await apiClient.put(`/expert_teams/members/${memberId}`, input))
}

export async function deleteExpertMember(memberId: number): Promise<void> {
  await apiClient.delete(`/expert_teams/members/${memberId}`)
}

// ─── 执行 ────────────────────────────────────────────────

export async function executeExpertTeam(teamId: number, input: ExpertTeamExecuteInput): Promise<ExpertTeamExecuteResult> {
  return extractData(await apiClient.post(`/expert_teams/${teamId}/execute`, input))
}

// ─── 运行记录 ────────────────────────────────────────────

export async function fetchExpertTeamRuns(
  teamId: number, params?: { page?: number; pageSize?: number }
): Promise<{ items: ExpertTeamRun[]; total: number }> {
  const { items, total } = extractPaginated(await apiClient.get(`/expert_teams/${teamId}/runs`, { params }) as any)
  return { items, total }
}

export async function fetchAllExpertRuns(params?: {
  status?: number; page?: number; pageSize?: number
}): Promise<{ items: ExpertTeamRun[]; total: number }> {
  const { items, total } = extractPaginated(await apiClient.get('/expert_teams/runs/all', { params }) as any)
  return { items, total }
}

export async function fetchExpertRunById(runId: number): Promise<ExpertTeamRun> {
  return extractData(await apiClient.get(`/expert_teams/runs/${runId}`))
}
