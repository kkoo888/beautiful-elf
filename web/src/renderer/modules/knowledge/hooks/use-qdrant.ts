import { useState, useCallback, useEffect } from 'react'
import { useMessage } from '@/hooks/use-message'
import {
  fetchQdrantStats,
  fetchDocumentVectorCounts,
  fetchDocumentVectors,
  deleteDocumentVectors,
  deleteVector,
  type QdrantCollectionStats,
  type DocumentVectorCount,
  type QdrantVectorRecord,
} from '../services/knowledge-api'

interface UseQdrantReturn {
  stats: QdrantCollectionStats | null
  docCounts: DocumentVectorCount[]
  activeDocId: number | null
  vectors: QdrantVectorRecord[]
  vectorsLoading: boolean
  vectorsNextOffset: string | null
  statsLoading: boolean
  docCountsLoading: boolean
  loadStats: () => void
  loadDocCounts: () => void
  selectDocument: (docId: number) => Promise<void>
  loadMoreVectors: () => Promise<void>
  handleDeleteDocVectors: (docId: number) => Promise<void>
  handleDeleteVector: (docId: number, pointId: string) => Promise<void>
  handleCloseVectors: () => void
}

export function useQdrant(): UseQdrantReturn {
  const { message } = useMessage()
  const [stats, setStats] = useState<QdrantCollectionStats | null>(null)
  const [docCounts, setDocCounts] = useState<DocumentVectorCount[]>([])
  const [activeDocId, setActiveDocId] = useState<number | null>(null)
  const [vectors, setVectors] = useState<QdrantVectorRecord[]>([])
  const [vectorsNextOffset, setVectorsNextOffset] = useState<string | null>(null)
  const [statsLoading, setStatsLoading] = useState(false)
  const [docCountsLoading, setDocCountsLoading] = useState(false)
  const [vectorsLoading, setVectorsLoading] = useState(false)

  const loadStats = useCallback(async () => {
    setStatsLoading(true)
    try {
      const data = await fetchQdrantStats()
      setStats(data)
    } catch {
      message.error('获取 Qdrant 状态失败')
    } finally {
      setStatsLoading(false)
    }
  }, [])

  const loadDocCounts = useCallback(async () => {
    setDocCountsLoading(true)
    try {
      const data = await fetchDocumentVectorCounts()
      setDocCounts(data)
    } catch {
      message.error('获取向量计数失败')
    } finally {
      setDocCountsLoading(false)
    }
  }, [])

  // 组件挂载时加载一次
  useEffect(() => {
    loadStats()
    loadDocCounts()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const selectDocument = useCallback(async (docId: number) => {
    setActiveDocId(docId)
    setVectors([])
    setVectorsNextOffset(null)
    setVectorsLoading(true)
    try {
      const resp = await fetchDocumentVectors(docId, null, 20)
      setVectors(resp.items)
      setVectorsNextOffset(resp.nextOffset)
    } catch {
      message.error('获取向量列表失败')
    } finally {
      setVectorsLoading(false)
    }
  }, [])

  const loadMoreVectors = useCallback(async () => {
    if (activeDocId === null || vectorsNextOffset === null) return
    setVectorsLoading(true)
    try {
      const resp = await fetchDocumentVectors(activeDocId, vectorsNextOffset, 20)
      setVectors((prev) => [...prev, ...resp.items])
      setVectorsNextOffset(resp.nextOffset)
    } catch {
      message.error('加载更多向量失败')
    } finally {
      setVectorsLoading(false)
    }
  }, [activeDocId, vectorsNextOffset])

  const refreshAll = useCallback(() => {
    loadStats()
    loadDocCounts()
  }, [loadStats, loadDocCounts])

  const handleDeleteDocVectors = useCallback(
    async (docId: number) => {
      try {
        const count = await deleteDocumentVectors(docId)
        message.success(`已删除 ${count} 个向量`)
        refreshAll()
        // 如果正在查看该文档的向量，清空
        if (activeDocId === docId) {
          setActiveDocId(null)
          setVectors([])
        }
      } catch {
        message.error('删除向量失败')
      }
    },
    [activeDocId, refreshAll],
  )

  const handleDeleteVector = useCallback(
    async (docId: number, pointId: string) => {
      try {
        await deleteVector(docId, pointId)
        message.success('向量已删除')
        // 从本地列表移除
        setVectors((prev) => prev.filter((v) => v.pointId !== pointId))
        refreshAll()
      } catch {
        message.error('删除向量失败')
      }
    },
    [refreshAll],
  )

  const handleCloseVectors = useCallback(() => {
    setActiveDocId(null)
    setVectors([])
    setVectorsNextOffset(null)
  }, [])

  return {
    stats,
    docCounts,
    activeDocId,
    vectors,
    vectorsLoading,
    vectorsNextOffset,
    statsLoading,
    docCountsLoading,
    loadStats,
    loadDocCounts,
    selectDocument,
    loadMoreVectors,
    handleDeleteDocVectors,
    handleDeleteVector,
    handleCloseVectors,
  }
}
