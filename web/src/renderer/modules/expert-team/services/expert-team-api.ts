/** 专家团工作流 API 服务 */

import { apiClient } from '@/services/api-client'
import type {
  ExpertTeam,
  ExpertTeamFormInput,
  ExpertTeamUpdateInput,
  ExpertMemberFormInput,
  ExpertTeamRun,
  ExpertTeamExecuteInput,
  ExpertTeamExecuteResult,
} from '../types'

// ─── 专家团 CRUD ─────────────────────────────────────────

/** 获取专家团列表 */
export async function fetchExpertTeams(params?: {
  category?: string
  enabled?: number
  page?: number
  pageSize?: number
}): Promise<{ items: ExpertTeam[]; total: number }> {
  const { data } = await apiClient.get('/expert_teams', { params })
  return data.data
}

/** 获取专家团详情 */
export async function fetchExpertTeamById(id: number): Promise<ExpertTeam> {
  const { data } = await apiClient.get(`/expert_teams/${id}`)
  return data.data
}

/** 创建专家团 */
export async function createExpertTeam(input: ExpertTeamFormInput): Promise<ExpertTeam> {
  const { data } = await apiClient.post('/expert_teams', input)
  return data.data
}

/** 更新专家团 */
export async function updateExpertTeam(
  id: number,
  input: ExpertTeamUpdateInput
): Promise<ExpertTeam> {
  const { data } = await apiClient.put(`/expert_teams/${id}`, input)
  return data.data
}

/** 删除专家团 */
export async function deleteExpertTeam(id: number): Promise<void> {
  await apiClient.delete(`/expert_teams/${id}`)
}

// ─── 专家成员 ────────────────────────────────────────────

/** 添加专家成员 */
export async function addExpertMember(
  teamId: number,
  input: ExpertMemberFormInput
): Promise<ExpertMemberFormInput> {
  const { data } = await apiClient.post(`/expert_teams/${teamId}/members`, input)
  return data.data
}

/** 更新专家成员 */
export async function updateExpertMember(
  memberId: number,
  input: Partial<ExpertMemberFormInput>
): Promise<ExpertMemberFormInput> {
  const { data } = await apiClient.put(`/expert_teams/members/${memberId}`, input)
  return data.data
}

/** 删除专家成员 */
export async function deleteExpertMember(memberId: number): Promise<void> {
  await apiClient.delete(`/expert_teams/members/${memberId}`)
}

// ─── 执行 ────────────────────────────────────────────────

/** 执行专家团工作流 */
export async function executeExpertTeam(
  teamId: number,
  input: ExpertTeamExecuteInput
): Promise<ExpertTeamExecuteResult> {
  const { data } = await apiClient.post(`/expert_teams/${teamId}/execute`, input)
  return data.data
}

// ─── 运行记录 ────────────────────────────────────────────

/** 获取专家团运行记录 */
export async function fetchExpertTeamRuns(
  teamId: number,
  params?: { page?: number; pageSize?: number }
): Promise<{ items: ExpertTeamRun[]; total: number }> {
  const { data } = await apiClient.get(`/expert_teams/${teamId}/runs`, { params })
  return data.data
}

/** 获取所有运行记录 */
export async function fetchAllExpertRuns(params?: {
  status?: number
  page?: number
  pageSize?: number
}): Promise<{ items: ExpertTeamRun[]; total: number }> {
  const { data } = await apiClient.get('/expert_teams/runs/all', { params })
  return data.data
}

/** 获取运行记录详情 */
export async function fetchExpertRunById(runId: number): Promise<ExpertTeamRun> {
  const { data } = await apiClient.get(`/expert_teams/runs/${runId}`)
  return data.data
}
