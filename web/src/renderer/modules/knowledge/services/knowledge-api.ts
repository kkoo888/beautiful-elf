import { apiClient, extractData, extractPaginated } from '@/services/api-client'
import { KNOWLEDGE_ENDPOINTS } from '@/services/endpoints'
import type { KnowledgeDocument, PaginatedResponse } from '@/types'

/** 分块响应 */
export interface KnowledgeChunk {
  id: number
  documentId: number
  chunkIndex: number
  contentPreview: string
}

/** 搜索结果 */
export interface KnowledgeSearchResult {
  documentId: number
  filename: string
  content: string
  score: number
}

/** 搜索响应 */
export interface KnowledgeSearchResponse {
  items: KnowledgeSearchResult[]
  total: number
}

/** 文档列表查询参数 */
export interface DocumentListParams {
  page?: number
  pageSize?: number
  status?: number | null
  deleted?: boolean
}

/** 获取文档列表 */
export async function fetchDocuments(
  params: DocumentListParams = {}
): Promise<PaginatedResponse<KnowledgeDocument>> {
  const { page = 1, pageSize = 10, status, deleted = false } = params
  const resp = await apiClient.get(KNOWLEDGE_ENDPOINTS.DOCUMENTS, {
    params: { page, pageSize, status, deleted },
  })
  return extractPaginated<KnowledgeDocument>(resp)
}

/** 上传文档 */
export async function uploadDocument(file: File): Promise<KnowledgeDocument> {
  const formData = new FormData()
  formData.append('file', file)

  const resp = await apiClient.post(KNOWLEDGE_ENDPOINTS.DOCUMENTS, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 300000, // 5 分钟超时（大文件）
  })
  return extractData<KnowledgeDocument>(resp)
}

/** 删除文档（软删除） */
export async function deleteDocument(id: string | number): Promise<void> {
  const resp = await apiClient.delete(KNOWLEDGE_ENDPOINTS.DOCUMENT(id))
  extractData(resp)
}

/** 恢复文档 */
export async function restoreDocument(id: string | number): Promise<void> {
  const resp = await apiClient.post(KNOWLEDGE_ENDPOINTS.RESTORE(id))
  extractData(resp)
}

/** 获取文档分块列表 */
export async function fetchChunks(documentId: string | number): Promise<KnowledgeChunk[]> {
  const resp = await apiClient.get(KNOWLEDGE_ENDPOINTS.CHUNKS(documentId))
  return extractData<KnowledgeChunk[]>(resp)
}

/** 语义搜索 */
export async function searchKnowledge(query: string, limit = 10): Promise<KnowledgeSearchResponse> {
  const resp = await apiClient.get(KNOWLEDGE_ENDPOINTS.SEARCH, {
    params: { q: query, limit },
  })
  return extractData<KnowledgeSearchResponse>(resp)
}

/** 导出知识库 */
export async function exportKnowledge(): Promise<Blob> {
  const resp = await apiClient.get(KNOWLEDGE_ENDPOINTS.SEARCH, {
    params: { q: '', limit: 1000 },
    responseType: 'blob',
  })
  return new Blob([JSON.stringify(resp.data, null, 2)], { type: 'application/json' })
}
