/** 专家团工作流 API 服务 */

import { apiClient } from '@/services/api-client'
import { EXPERT_TEAM_ENDPOINTS } from '@/services/endpoints'
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
  const { data } = await apiClient.get(EXPERT_TEAM_ENDPOINTS.LIST, { params })
  return data.data
}

/** 获取专家团详情 */
export async function fetchExpertTeamById(id: number): Promise<ExpertTeam> {
  const { data } = await apiClient.get(EXPERT_TEAM_ENDPOINTS.DETAIL(String(id)))
  return data.data
}

/** 创建专家团 */
export async function createExpertTeam(input: ExpertTeamFormInput): Promise<ExpertTeam> {
  const { data } = await apiClient.post(EXPERT_TEAM_ENDPOINTS.CREATE, input)
  return data.data
}

/** 更新专家团 */
export async function updateExpertTeam(
  id: number,
  input: ExpertTeamUpdateInput
): Promise<ExpertTeam> {
  const { data } = await apiClient.put(EXPERT_TEAM_ENDPOINTS.DETAIL(String(id)), input)
  return data.data
}

/** 删除专家团 */
export async function deleteExpertTeam(id: number): Promise<void> {
  await apiClient.delete(EXPERT_TEAM_ENDPOINTS.DETAIL(String(id)))
}

// ─── 专家成员 ────────────────────────────────────────────

/** 添加专家成员 */
export async function addExpertMember(
  teamId: number,
  input: ExpertMemberFormInput
): Promise<ExpertMemberFormInput> {
  const { data } = await apiClient.post(
    EXPERT_TEAM_ENDPOINTS.MEMBERS(String(teamId)),
    input
  )
  return data.data
}

/** 更新专家成员 */
export async function updateExpertMember(
  memberId: number,
  input: Partial<ExpertMemberFormInput>
): Promise<ExpertMemberFormInput> {
  const { data } = await apiClient.put(
    EXPERT_TEAM_ENDPOINTS.MEMBER_DETAIL(String(memberId)),
    input
  )
  return data.data
}

/** 删除专家成员 */
export async function deleteExpertMember(memberId: number): Promise<void> {
  await apiClient.delete(EXPERT_TEAM_ENDPOINTS.MEMBER_DETAIL(String(memberId)))
}

// ─── 执行 ────────────────────────────────────────────────

/** 执行专家团工作流 */
export async function executeExpertTeam(
  teamId: number,
  input: ExpertTeamExecuteInput
): Promise<ExpertTeamExecuteResult> {
  const { data } = await apiClient.post(
    EXPERT_TEAM_ENDPOINTS.EXECUTE(String(teamId)),
    input
  )
  return data.data
}

// ─── 运行记录 ────────────────────────────────────────────

/** 获取专家团运行记录 */
export async function fetchExpertTeamRuns(
  teamId: number,
  params?: { page?: number; pageSize?: number }
): Promise<{ items: ExpertTeamRun[]; total: number }> {
  const { data } = await apiClient.get(
    EXPERT_TEAM_ENDPOINTS.RUNS(String(teamId)),
    { params }
  )
  return data.data
}

/** 获取所有运行记录 */
export async function fetchAllExpertRuns(params?: {
  status?: number
  page?: number
  pageSize?: number
}): Promise<{ items: ExpertTeamRun[]; total: number }> {
  const { data } = await apiClient.get(EXPERT_TEAM_ENDPOINTS.RUNS_ALL, { params })
  return data.data
}

/** 获取运行记录详情 */
export async function fetchExpertRunById(runId: number): Promise<ExpertTeamRun> {
  const { data } = await apiClient.get(
    EXPERT_TEAM_ENDPOINTS.RUN_DETAIL(String(runId))
  )
  return data.data
}
