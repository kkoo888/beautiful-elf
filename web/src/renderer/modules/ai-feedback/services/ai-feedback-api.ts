/**
 * AI 反馈 API 服务
 * 后端 Query: page, page_size, feedback_type
 */

import { apiClient, extractData, extractPaginated } from '@/services/api-client'
import type { AIFeedback, AIFeedbackStats } from '../types/ai_feedback'

export async function createAIFeedback(data: {
  conversationId: number | null; question: string; answer: string
  feedbackType: number; reasonTags: string[] | null; reasonText: string; traceId: string
}): Promise<AIFeedback> {
  return extractData(await apiClient.post('/ai_feedback/', data))
}

export async function fetchAIFeedbacks(params: {
  page?: number; pageSize?: number; feedbackType?: number
} = {}): Promise<{ items: AIFeedback[]; total: number }> {
  const { items, total } = extractPaginated(await apiClient.get('/ai_feedback/', {
    params: { page: params.page, pageSize: params.pageSize, feedbackType: params.feedbackType },
  }) as any)
  return { items, total }
}

export async function fetchAIFeedbackById(id: number): Promise<AIFeedback> {
  return extractData(await apiClient.get(`/ai_feedback/${id}`))
}

export async function fetchAIFeedbackStats(): Promise<AIFeedbackStats> {
  return extractData(await apiClient.get('/ai_feedback/stats'))
}
