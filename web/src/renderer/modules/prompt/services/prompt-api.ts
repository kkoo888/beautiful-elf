import { apiClient } from '@/services/api-client'
import type { Prompt } from '../types/prompt'

export async function createPrompt(data: {
  name: string
  content: string
  description: string
}): Promise<Prompt> {
  const resp = await apiClient.post('/prompts/', data)
  return (resp.data as any).data
}

export async function fetchPrompts(params: {
  page?: number
  pageSize?: number
  name?: string
} = {}): Promise<{ data: Prompt[]; total: number }> {
  const resp = await apiClient.get('/prompts/', { params })
  return {
    data: (resp.data as any).data,
    total: (resp.data as any).total,
  }
}

export async function fetchPromptById(id: number): Promise<Prompt> {
  const resp = await apiClient.get(`/prompts/${id}`)
  return (resp.data as any).data
}

export async function updatePrompt(
  id: number,
  data: { content: string; description: string }
): Promise<Prompt> {
  const resp = await apiClient.put(`/prompts/${id}`, data)
  return (resp.data as any).data
}

export async function deletePrompt(id: number): Promise<void> {
  await apiClient.delete(`/prompts/${id}`)
}

export async function activatePrompt(id: number): Promise<Prompt> {
  const resp = await apiClient.patch(`/prompts/${id}/activate`)
  return (resp.data as any).data
}

export async function fetchActivePrompt(name: string): Promise<Prompt> {
  const resp = await apiClient.get('/prompts/active', { params: { name } })
  return (resp.data as any).data
}

export async function fetchPromptVersions(name: string): Promise<Prompt[]> {
  const resp = await apiClient.get('/prompts/versions', { params: { name } })
  return (resp.data as any).data
}
