import { useState, useCallback, useEffect, useRef } from 'react'
import { useMessage } from '@/hooks/use-message'
import type { KnowledgeDocument } from '@/types'
import type { KnowledgeChunk } from '../services/knowledge-api'
import {
  fetchDocuments,
  fetchDocument,
  uploadDocument,
  deleteDocument,
  restoreDocument,
  fetchChunks,
  exportKnowledge,
} from '../services/knowledge-api'

interface UseKnowledgeReturn {
  documents: KnowledgeDocument[]
  loading: boolean
  total: number
  page: number
  pageSize: number
  showRecycle: boolean
  chunks: KnowledgeChunk[]
  chunksLoading: boolean
  activeDocId: number | null

  setPage: (page: number) => void
  setPageSize: (size: number) => void
  toggleRecycle: () => void
  refresh: () => void
  handleUpload: (file: File) => Promise<void>
  handleDelete: (id: number) => Promise<void>
  handleRestore: (id: number) => Promise<void>
  handleViewChunks: (id: number) => Promise<void>
  handleCloseChunks: () => void
  handleExport: () => Promise<void>
}

export function useKnowledge(): UseKnowledgeReturn {
  const { message } = useMessage()
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([])
  const [loading, setLoading] = useState(false)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [showRecycle, setShowRecycle] = useState(false)
  const [chunks, setChunks] = useState<KnowledgeChunk[]>([])
  const [chunksLoading, setChunksLoading] = useState(false)
  const [activeDocId, setActiveDocId] = useState<number | null>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const loadDocuments = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetchDocuments({
        page,
        pageSize,
        deleted: showRecycle,
      })
      setDocuments(res.items)
      setTotal(res.total)
    } catch {
      message.error('加载文档列表失败')
    } finally {
      setLoading(false)
    }
  }, [page, pageSize, showRecycle])

  useEffect(() => {
    loadDocuments()
  }, [loadDocuments])

  // 组件卸载时清理轮询定时器
  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [])

  const refresh = useCallback(() => {
    loadDocuments()
  }, [loadDocuments])

  const startPolling = useCallback(
    (docId: number) => {
      if (pollRef.current) clearInterval(pollRef.current)
      pollRef.current = setInterval(async () => {
        try {
          const doc = await fetchDocument(docId)
          if (doc.status >= 2) {
            // status 2=就绪, 3=失败 — 统一清理定时器
            clearInterval(pollRef.current!)
            pollRef.current = null
            if (doc.status === 2) {
              message.success(`"${doc.filename}" 处理完成`)
            } else {
              message.error(`"${doc.filename}" 处理失败`)
            }
            loadDocuments()
          }
          // status 0/1 → 继续轮询
        } catch {
          // 网络异常不停止轮询，继续重试
        }
      }, 3000)
    },
    [loadDocuments]
  )

  const handleUpload = useCallback(
    async (file: File) => {
      try {
        const doc = await uploadDocument(file)
        message.success(`文档 "${file.name}" 上传成功`)
        loadDocuments()
        if (doc.status < 2) {
          startPolling(doc.id)
        }
      } catch {
        message.error('上传失败')
      }
    },
    [loadDocuments, startPolling]
  )

  const handleDelete = useCallback(
    async (id: number) => {
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
    async (id: number) => {
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

  const handleViewChunks = useCallback(async (id: number) => {
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
    showRecycle,
    chunks,
    chunksLoading,
    activeDocId,
    setPage,
    setPageSize,
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
