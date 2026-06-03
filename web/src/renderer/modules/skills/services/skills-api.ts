/**
 * 技能 API 服务
 *
 * 使用 extractData / extractPaginated 消除 as any。
 */

import { apiClient, extractData, extractPaginated } from '@/services/api-client'
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
  const resp = await apiClient.get('/skills', {
    params: { page: params?.page ?? 1, pageSize: params?.pageSize ?? 20, isEnabled: params?.isEnabled },
  })
  const { items, total, page, pageSize } = extractPaginated(resp as any)
  return { data: items, total, page, pageSize }
}

/** 创建技能 */
export async function createSkill(input: CreateSkillInput): Promise<Skill> {
  return extractData(await apiClient.post('/skills', input))
}

/** 更新技能 */
export async function updateSkill(id: string, input: UpdateSkillInput): Promise<Skill> {
  return extractData(await apiClient.put(`/skills/${id}`, input))
}

/** 删除技能 */
export async function deleteSkill(id: string): Promise<void> {
  await apiClient.delete(`/skills/${id}`)
}

/** 启用技能 */
export async function enableSkill(id: string): Promise<Skill> {
  return extractData(await apiClient.patch(`/skills/${id}/enable`))
}

/** 禁用技能 */
export async function disableSkill(id: string): Promise<Skill> {
  return extractData(await apiClient.patch(`/skills/${id}/disable`))
}

/** 获取技能统计 */
export async function fetchSkillStats(id: string): Promise<SkillStats> {
  return extractData(await apiClient.get(`/skills/${id}/stats`))
}

/** 记录技能调用 */
export async function recordSkillCall(id: string, success: boolean, durationMs: number): Promise<void> {
  await apiClient.post(`/skills/${id}/stats/record`, null, {
    params: { success, durationMs },
  })
}

/** 安装技能 */
export async function installSkill(input: InstallSkillInput): Promise<Skill> {
  const name = input.source === 'github'
    ? input.content.split('/').pop()?.replace('.git', '') || 'imported-skill'
    : `imported-${Date.now()}`
  return extractData(await apiClient.post('/skills', {
    name,
    displayName: name,
    description: `从${input.source === 'github' ? 'GitHub' : '文件'}导入`,
    source: input.source,
    config: { content: input.content },
  }))
}

/** 切换技能启用/禁用状态 */
export async function toggleSkill(id: string, enabled: boolean): Promise<Skill> {
  return extractData(await apiClient.patch(`/skills/${id}/toggle`, { enabled }))
}

/** 炼化技能（LLM 优化建议） */
export async function refineSkill(id: string, prompt?: string): Promise<RefineResult> {
  return extractData(await apiClient.post(`/skills/${id}/refine`, { prompt }))
}
