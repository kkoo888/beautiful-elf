/** 记忆模块类型定义 */

/** 记忆条目 */
export interface MemoryEntry {
  /** 唯一标识 */
  id: string
  /** 摘要文本 */
  summary: string
  /** 完整记忆内容 */
  content: string
  /** 来源会话 ID */
  conversationId: string
  /** 关联标签 */
  tags: string[]
  /** 语义搜索时的相似度（0-1） */
  similarity?: number
  /** 创建时间 ISO 字符串 */
  createdAt: string
}

/** 记忆列表查询参数 */
export interface MemoryQueryParams {
  /** 页码 */
  page?: number
  /** 每页条数 */
  pageSize?: number
  /** 关键词筛选 */
  keyword?: string
  /** 标签筛选 */
  tag?: string
}

/** 记忆列表响应 */
export interface MemoryListResponse {
  items: MemoryEntry[]
  total: number
  page: number
  pageSize: number
}

/** 语义搜索结果 */
export interface MemorySearchResult {
  items: MemoryEntry[]
  query: string
}

/** Episode 对话分组 */
export interface MemoryEpisode {
  /** 唯一标识 */
  id: number
  /** 关联会话 ID */
  conversationId: string
  /** 标题 */
  title: string
  /** 摘要 */
  summary: string
  /** 开始时间 */
  startedAt: string
  /** 结束时间 */
  endedAt: string
  /** 关联实体 ID（逗号分隔） */
  entityIds: string
  /** 关联观察 ID（逗号分隔） */
  observationIds: string
  /** 创建时间 */
  createdAt: string
}

/** Insight 演化历史 */
export interface MemoryInsightHistory {
  /** 唯一标识 */
  id: number
  /** 关联洞察 ID */
  insightId: number
  /** 操作类型 */
  action: 'created' | 'reinforced' | 'weakened' | 'contradicted' | 'superseded' | 'merged'
  /** 旧置信度 */
  oldConfidence: number
  /** 新置信度 */
  newConfidence: number
  /** 操作原因 */
  reason: string
  /** 触发观察 ID */
  triggerObsIds: number[]
  /** 时间戳 */
  timestamp: string
}

/** 优化结果 */
export interface OptimizationResult {
  /** 优化记忆数量 */
  optimizedCount: number
  /** Rerank 改进数量 */
  rerankImproved: number
  /** Decay 应用数量 */
  decayApplied: number
  /** 新增洞察数量 */
  newInsights: number
}
