/**
 * 技能 API 服务
 *
 * 后端 Query 参数: page, page_size, is_enabled → snake_case
 */

import { apiClient, extractData, extractPaginated } from '@/services/api-client'
import type {
  Skill, SkillStats, SkillQueryParams, CreateSkillInput, UpdateSkillInput,
  InstallSkillInput, RefineResult, PaginatedResult,
} from '../types/skills'

/** 获取技能列表（分页） */
export async function fetchSkills(params?: SkillQueryParams): Promise<PaginatedResult<Skill>> {
  const resp = await apiClient.get('/skills', {
    params: { page: params?.page ?? 1, page_size: params?.pageSize ?? 20, is_enabled: params?.isEnabled },
  })
  const { items, total, page, pageSize } = extractPaginated(resp as any)
  return { data: items, total, page, pageSize }
}

export async function createSkill(input: CreateSkillInput): Promise<Skill> {
  return extractData(await apiClient.post('/skills', input))
}

export async function updateSkill(id: string, input: UpdateSkillInput): Promise<Skill> {
  return extractData(await apiClient.put(`/skills/${id}`, input))
}

export async function deleteSkill(id: string): Promise<void> {
  await apiClient.delete(`/skills/${id}`)
}

export async function enableSkill(id: string): Promise<Skill> {
  return extractData(await apiClient.patch(`/skills/${id}/enable`))
}

export async function disableSkill(id: string): Promise<Skill> {
  return extractData(await apiClient.patch(`/skills/${id}/disable`))
}

export async function fetchSkillStats(id: string): Promise<SkillStats> {
  return extractData(await apiClient.get(`/skills/${id}/stats`))
}

export async function recordSkillCall(id: string, success: boolean, durationMs: number): Promise<void> {
  await apiClient.post(`/skills/${id}/stats/record`, null, { params: { success, duration_ms: durationMs } })
}

export async function installSkill(input: InstallSkillInput): Promise<Skill> {
  const name = input.source === 'github'
    ? input.content.split('/').pop()?.replace('.git', '') || 'imported-skill'
    : `imported-${Date.now()}`
  return extractData(await apiClient.post('/skills', {
    name, displayName: name, description: `从${input.source === 'github' ? 'GitHub' : '文件'}导入`,
    source: input.source, config: { content: input.content },
  }))
}

export async function toggleSkill(id: string, enabled: boolean): Promise<Skill> {
  return extractData(await apiClient.patch(`/skills/${id}/toggle`, { enabled }))
}

export async function refineSkill(id: string, prompt?: string): Promise<RefineResult> {
  return extractData(await apiClient.post(`/skills/${id}/refine`, { prompt }))
}
