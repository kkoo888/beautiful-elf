import { useState, useCallback, useEffect } from 'react'
import { useMessage } from '@/hooks/use-message'
import type {
  KnowledgeDocument,
  KnowledgeChunk,
  DocumentListParams,
  KnowledgeFileType,
} from '../types/knowledge'
import {
  fetchDocuments,
  uploadDocument,
  deleteDocument,
  restoreDocument,
  fetchChunks,
  exportKnowledge,
} from '../services/knowledge-api'

interface UseKnowledgeReturn {
  /** 文档列表 */
  documents: KnowledgeDocument[]
  /** 加载中 */
  loading: boolean
  /** 总数 */
  total: number
  /** 当前页 */
  page: number
  /** 每页条数 */
  pageSize: number
  /** 搜索关键词 */
  keyword: string
  /** 文件类型筛选 */
  fileType: KnowledgeFileType | undefined
  /** 是否显示回收站 */
  showRecycle: boolean
  /** 分块数据 */
  chunks: KnowledgeChunk[]
  /** 分块加载中 */
  chunksLoading: boolean
  /** 当前查看分块的文档 */
  activeDocId: string | null

  /** 设置页码 */
  setPage: (page: number) => void
  /** 设置每页条数 */
  setPageSize: (size: number) => void
  /** 设置关键词 */
  setKeyword: (keyword: string) => void
  /** 设置文件类型筛选 */
  setFileType: (type: KnowledgeFileType | undefined) => void
  /** 切换回收站 */
  toggleRecycle: () => void
  /** 刷新列表 */
  refresh: () => void
  /** 上传文件 */
  handleUpload: (file: File) => Promise<void>
  /** 删除文档 */
  handleDelete: (id: string) => Promise<void>
  /** 恢复文档 */
  handleRestore: (id: string) => Promise<void>
  /** 查看分块 */
  handleViewChunks: (id: string) => Promise<void>
  /** 关闭分块抽屉 */
  handleCloseChunks: () => void
  /** 导出知识库 */
  handleExport: () => Promise<void>
}

export function useKnowledge(): UseKnowledgeReturn {
  const { message } = useMessage()
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([])
  const [loading, setLoading] = useState(false)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [keyword, setKeyword] = useState('')
  const [fileType, setFileType] = useState<KnowledgeFileType | undefined>()
  const [showRecycle, setShowRecycle] = useState(false)
  const [chunks, setChunks] = useState<KnowledgeChunk[]>([])
  const [chunksLoading, setChunksLoading] = useState(false)
  const [activeDocId, setActiveDocId] = useState<string | null>(null)

  const loadDocuments = useCallback(async () => {
    setLoading(true)
    try {
      const params: DocumentListParams = {
        page,
        pageSize,
        keyword: keyword || undefined,
        fileType,
        deleted: showRecycle,
      }
      const res = await fetchDocuments(params)
      setDocuments(res.data)
      setTotal(res.total)
    } catch {
      message.error('加载文档列表失败')
    } finally {
      setLoading(false)
    }
  }, [page, pageSize, keyword, fileType, showRecycle])

  useEffect(() => {
    loadDocuments()
  }, [loadDocuments])

  const refresh = useCallback(() => {
    loadDocuments()
  }, [loadDocuments])

  const handleUpload = useCallback(
    async (file: File) => {
      try {
        await uploadDocument(file)
        message.success(`文档 "${file.name}" 上传成功`)
        loadDocuments()
      } catch {
        message.error('上传失败')
      }
    },
    [loadDocuments]
  )

  const handleDelete = useCallback(
    async (id: string) => {
      try {
        await deleteDocument(id)
        message.success('已移入回收站')
        loadDocuments()
      } catch {
        message.error('删除失败')
      }
    },
    [loadDocuments]
  )

  const handleRestore = useCallback(
    async (id: string) => {
      try {
        await restoreDocument(id)
        message.success('文档已恢复')
        loadDocuments()
      } catch {
        message.error('恢复失败')
      }
    },
    [loadDocuments]
  )

  const handleViewChunks = useCallback(async (id: string) => {
    setActiveDocId(id)
    setChunksLoading(true)
    try {
      const data = await fetchChunks(id)
      setChunks(data)
    } catch {
      message.error('加载分块失败')
    } finally {
      setChunksLoading(false)
    }
  }, [])

  const handleCloseChunks = useCallback(() => {
    setActiveDocId(null)
    setChunks([])
  }, [])

  const handleExport = useCallback(async () => {
    try {
      const blob = await exportKnowledge()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `knowledge-export-${Date.now()}.json`
      a.click()
      URL.revokeObjectURL(url)
      message.success('导出成功')
    } catch {
      message.error('导出失败')
    }
  }, [])

  const toggleRecycle = useCallback(() => {
    setShowRecycle((prev) => !prev)
    setPage(1)
  }, [])

  return {
    documents,
    loading,
    total,
    page,
    pageSize,
    keyword,
    fileType,
    showRecycle,
    chunks,
    chunksLoading,
    activeDocId,
    setPage,
    setPageSize,
    setKeyword,
    setFileType,
    toggleRecycle,
    refresh,
    handleUpload,
    handleDelete,
    handleRestore,
    handleViewChunks,
    handleCloseChunks,
    handleExport,
  }
}
