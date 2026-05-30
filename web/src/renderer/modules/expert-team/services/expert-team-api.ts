/** 专家团工作流 API 服务 */

import { apiClient } from '@/services/api-client'
import { API_PREFIX } from '@shared/constants'
import type {
  ExpertTeam,
  ExpertTeamFormInput,
  ExpertTeamUpdateInput,
  ExpertMemberFormInput,
  ExpertTeamRun,
  ExpertTeamExecuteInput,
} from '../types'

const BASE = `${API_PREFIX}/expert_teams`

// ─── 专家团 CRUD ─────────────────────────────────────────

/** 获取专家团列表 */
export async function fetchExpertTeams(params?: {
  category?: string
  enabled?: number
  page?: number
  page_size?: number
}): Promise<{ items: ExpertTeam[]; total: number }> {
  const { data } = await apiClient.get(BASE, { params })
  return data.data
}

/** 获取专家团详情 */
export async function fetchExpertTeamById(id: number): Promise<ExpertTeam> {
  const { data } = await apiClient.get(`${BASE}/${id}`)
  return data.data
}

/** 创建专家团 */
export async function createExpertTeam(input: ExpertTeamFormInput): Promise<ExpertTeam> {
  const { data } = await apiClient.post(BASE, input)
  return data.data
}

/** 更新专家团 */
export async function updateExpertTeam(
  id: number,
  input: ExpertTeamUpdateInput
): Promise<ExpertTeam> {
  const { data } = await apiClient.put(`${BASE}/${id}`, input)
  return data.data
}

/** 删除专家团 */
export async function deleteExpertTeam(id: number): Promise<void> {
  await apiClient.delete(`${BASE}/${id}`)
}

// ─── 专家成员 ────────────────────────────────────────────

/** 添加专家成员 */
export async function addExpertMember(
  teamId: number,
  input: ExpertMemberFormInput
): Promise<ExpertMemberFormInput> {
  const { data } = await apiClient.post(`${BASE}/${teamId}/members`, input)
  return data.data
}

/** 更新专家成员 */
export async function updateExpertMember(
  memberId: number,
  input: Partial<ExpertMemberFormInput>
): Promise<ExpertMemberFormInput> {
  const { data } = await apiClient.put(`${BASE}/members/${memberId}`, input)
  return data.data
}

/** 删除专家成员 */
export async function deleteExpertMember(memberId: number): Promise<void> {
  await apiClient.delete(`${BASE}/members/${memberId}`)
}

// ─── 执行 ────────────────────────────────────────────────

/** 执行专家团工作流 */
export async function executeExpertTeam(
  teamId: number,
  input: ExpertTeamExecuteInput
): Promise<{
  run_id: number
  status: number
  output: string
  discussion: Array<{
    round: number
    expert_name: string
    expert_role: string
    content: string
    timestamp: string
  }>
  rounds: number
  token_usage: number
  duration_ms: number
}> {
  const { data } = await apiClient.post(`${BASE}/${teamId}/execute`, input)
  return data.data
}

// ─── 运行记录 ────────────────────────────────────────────

/** 获取专家团运行记录 */
export async function fetchExpertTeamRuns(
  teamId: number,
  params?: { page?: number; page_size?: number }
): Promise<{ items: ExpertTeamRun[]; total: number }> {
  const { data } = await apiClient.get(`${BASE}/${teamId}/runs`, { params })
  return data.data
}

/** 获取所有运行记录 */
export async function fetchAllExpertRuns(params?: {
  status?: number
  page?: number
  page_size?: number
}): Promise<{ items: ExpertTeamRun[]; total: number }> {
  const { data } = await apiClient.get(`${BASE}/runs/all`, { params })
  return data.data
}

/** 获取运行记录详情 */
export async function fetchExpertRunById(runId: number): Promise<ExpertTeamRun> {
  const { data } = await apiClient.get(`${BASE}/runs/${runId}`)
  return data.data
}
