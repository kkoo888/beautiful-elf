/**
 * Prompt 版本管理 API 服务
 */

import { apiClient, extractData, extractPaginated } from '@/services/api-client'
import type { Prompt } from '../types/prompt'

export async function createPrompt(data: {
  name: string
  content: string
  description: string
}): Promise<Prompt> {
  return extractData(await apiClient.post('/prompts/', data))
}

export async function fetchPrompts(params: {
  page?: number
  pageSize?: number
  name?: string
} = {}): Promise<{ items: Prompt[]; total: number }> {
  const { items, total } = extractPaginated(await apiClient.get('/prompts/', { params }) as any)
  return { items, total }
}

export async function fetchPromptById(id: number): Promise<Prompt> {
  return extractData(await apiClient.get(`/prompts/${id}`))
}

export async function updatePrompt(
  id: number,
  data: { content: string; description: string }
): Promise<Prompt> {
  return extractData(await apiClient.put(`/prompts/${id}`, data))
}

export async function deletePrompt(id: number): Promise<void> {
  await apiClient.delete(`/prompts/${id}`)
}

export async function activatePrompt(id: number): Promise<Prompt> {
  return extractData(await apiClient.patch(`/prompts/${id}/activate`))
}

export async function fetchActivePrompt(name: string): Promise<Prompt> {
  return extractData(await apiClient.get('/prompts/active', { params: { name } }))
}

export async function fetchPromptVersions(name: string): Promise<Prompt[]> {
  return extractData(await apiClient.get('/prompts/versions', { params: { name } }))
}
