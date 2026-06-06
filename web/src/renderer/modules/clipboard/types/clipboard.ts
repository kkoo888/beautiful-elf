/** 剪贴板内容类型 */
export type ClipboardContentType = 'text' | 'code' | 'image' | 'link'

/** 剪贴板条目 */
export interface ClipboardItem {
  id: number
  content: string
  contentType: ClipboardContentType
  /** 代码语言标识（仅 contentType === 'code' 时有效） */
  language?: string
  isPinned: number
  copiedAt: string
  createdAt: string
}

/** 分页请求参数 */
export interface ClipboardListParams {
  page?: number
  pageSize?: number
  /** 搜索关键词 */
  keyword?: string
}

/** 分页响应 */
export interface ClipboardListResponse {
  items: ClipboardItem[]
  total: number
  page: number
  pageSize: number
}
