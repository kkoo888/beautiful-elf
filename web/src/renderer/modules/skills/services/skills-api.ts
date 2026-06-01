/** 技能 API 服务 */

import { apiClient } from '@/services/api-client'
import type {
  Skill,
  SkillStats,
  SkillQueryParams,
  CreateSkillInput,
  UpdateSkillInput,
  InstallSkillInput,
  RefineResult,
  PaginatedResult,
} from '../types/skills'

/** 获取技能列表（分页） */
export async function fetchSkills(params?: SkillQueryParams): Promise<PaginatedResult<Skill>> {
  const resp = await apiClient.get('/skills', { params: { page: params?.page ?? 1, pageSize: params?.pageSize ?? 20, isEnabled: params?.isEnabled } })
  const body = resp.data as any
  return {
    data: body.data,
    total: body.total,
    page: body.page,
    pageSize: body.pageSize,
  }
}

/** 创建技能 */
export async function createSkill(input: CreateSkillInput): Promise<Skill> {
  const resp = await apiClient.post('/skills', input)
  return (resp.data as any).data
}

/** 更新技能 */
export async function updateSkill(id: string, input: UpdateSkillInput): Promise<Skill> {
  const resp = await apiClient.put(`/skills/${id}`, input)
  return (resp.data as any).data
}

/** 删除技能 */
export async function deleteSkill(id: string): Promise<void> {
  await apiClient.delete(`/skills/${id}`)
}

/** 启用技能 */
export async function enableSkill(id: string): Promise<Skill> {
  const resp = await apiClient.patch(`/skills/${id}/enable`)
  return (resp.data as any).data
}

/** 禁用技能 */
export async function disableSkill(id: string): Promise<Skill> {
  const resp = await apiClient.patch(`/skills/${id}/disable`)
  return (resp.data as any).data
}

/** 获取技能统计 */
export async function fetchSkillStats(id: string): Promise<SkillStats> {
  const resp = await apiClient.get(`/skills/${id}/stats`)
  return (resp.data as any).data
}

/** 记录技能调用 */
export async function recordSkillCall(id: string, success: boolean, durationMs: number): Promise<void> {
  await apiClient.post(`/skills/${id}/stats/record`, null, {
    params: { success, durationMs },
  })
}

/** 安装技能 */
export async function installSkill(input: InstallSkillInput): Promise<Skill> {
  const resp = await apiClient.post('/skills/install', input)
  return (resp.data as any).data
}

/** 切换技能启用/禁用状态 */
export async function toggleSkill(id: string, enabled: boolean): Promise<Skill> {
  const resp = await apiClient.patch(`/skills/${id}/toggle`, { enabled })
  return (resp.data as any).data
}

/** 炼化技能（LLM 优化建议） */
export async function refineSkill(id: string, prompt?: string): Promise<RefineResult> {
  const resp = await apiClient.post(`/skills/${id}/refine`, { prompt })
  return (resp.data as any).data
}
