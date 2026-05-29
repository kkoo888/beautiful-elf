export interface AIFeedback {
  id: number
  conversationId: number | null
  question: string
  answer: string
  feedbackType: number // 0=点赞, 1=踩
  reasonTags: string[] | null
  reasonText: string
  traceId: string
  createdAt: string
  updatedAt: string
}

export interface AIFeedbackStats {
  total: number
  likeCount: number
  dislikeCount: number
  likeRate: number
  tagCounts: Record<string, number>
}
