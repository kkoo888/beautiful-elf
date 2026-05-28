/** 知识库文档类型 */
export type KnowledgeFileType = 'pdf' | 'docx' | 'md' | 'txt' | 'json' | 'csv' | 'yaml' | 'html' | 'xml' | 'zip'

/** 文档状态 */
export type DocumentStatus = 'indexing' | 'ready' | 'error'

/** 知识库文档 */
export interface KnowledgeDocument {
  id: string
  fileName: string
  fileType: KnowledgeFileType
  chunkCount: number
  status: DocumentStatus
  deleted: boolean
  createdAt: string
  updatedAt: string
}

/** 知识块 */
export interface KnowledgeChunk {
  id: string
  documentId: string
  chunkIndex: number
  content: string
}

/** 文档列表查询参数 */
export interface DocumentListParams {
  page?: number
  pageSize?: number
  keyword?: string
  fileType?: KnowledgeFileType
  deleted?: boolean
}

/** 分页响应 */
export interface PaginatedResponse<T> {
  data: T[]
  total: number
  page: number
  pageSize: number
}

/** 文件类型映射 */
export const FILE_TYPE_EXTENSIONS: Record<KnowledgeFileType, string> = {
  pdf: '.pdf',
  docx: '.docx',
  md: '.md',
  txt: '.txt',
  json: '.json',
  csv: '.csv',
  yaml: '.yaml',
  html: '.html',
  xml: '.xml',
  zip: '.zip',
}

/** 文件类型图标 */
export const FILE_TYPE_ICONS: Record<KnowledgeFileType, string> = {
  pdf: '📄',
  docx: '📝',
  md: '📑',
  txt: '📃',
  json: '🔧',
  csv: '📊',
  yaml: '⚙️',
  html: '🌐',
  xml: '📋',
  zip: '📦',
}

/** 支持的文件扩展名列表 */
export const SUPPORTED_EXTENSIONS = Object.values(FILE_TYPE_EXTENSIONS)

/** 最大文件大小 (20MB) */
export const MAX_FILE_SIZE = 20 * 1024 * 1024
