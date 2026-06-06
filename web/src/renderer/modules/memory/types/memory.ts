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
