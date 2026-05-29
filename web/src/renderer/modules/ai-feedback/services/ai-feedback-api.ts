import { apiClient } from '@/services/api-client'
import type { AIFeedback, AIFeedbackStats } from '../types/ai-feedback'

export async function createAIFeedback(data: {
  conversationId: number | null
  question: string
  answer: string
  feedbackType: number
  reasonTags: string[] | null
  reasonText: string
  traceId: string
}): Promise<AIFeedback> {
  const resp = await apiClient.post('/ai-feedback/', data)
  return (resp.data as any).data
}

export async function fetchAIFeedbacks(params: {
  page?: number
  pageSize?: number
  feedbackType?: number
} = {}): Promise<{ data: AIFeedback[]; total: number }> {
  const resp = await apiClient.get('/ai-feedback/', { params })
  return {
    data: (resp.data as any).data,
    total: (resp.data as any).total,
  }
}

export async function fetchAIFeedbackById(id: number): Promise<AIFeedback> {
  const resp = await apiClient.get(`/ai-feedback/${id}`)
  return (resp.data as any).data
}

export async function fetchAIFeedbackStats(): Promise<AIFeedbackStats> {
  const resp = await apiClient.get('/ai-feedback/stats')
  return (resp.data as any).data
}
