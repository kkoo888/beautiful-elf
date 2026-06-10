import { useMemo } from 'react'
import { Input, Select, Segmented, Space } from 'antd'
import { DatabaseOutlined, FileTextOutlined, AppstoreOutlined } from '@ant-design/icons'
import { PageHeader } from '@/components/page-header'
import { EmptyState } from '@/components/empty-state'
import { useKnowledge } from '../hooks/use-knowledge'
import { DocumentUpload } from './document-upload'
import { DocumentList } from './document-list'
import { DocumentDetail } from './document-detail'
import { RecycleBin } from './recycle-bin'
import { ExportButton } from './export-button'
import styles from './knowledge-panel.module.css'

/**
 * 知识库主面板
 */
export function KnowledgePanel() {
  const {
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
    handleUpload,
    handleDelete,
    handleRestore,
    handleViewChunks,
    handleCloseChunks,
    handleExport,
  } = useKnowledge()

  const stats = useMemo(() => {
    const totalChunks = documents.reduce((sum, doc) => sum + (doc.chunkCount || 0), 0)
    const readyCount = documents.filter((doc) => doc.status === 2).length
    return { total, totalChunks, readyCount }
  }, [documents, total])

  const handlePageChange = (p: number, ps: number) => {
    setPage(p)
    setPageSize(ps)
  }

  return (
    <div className={styles.panel}>
      <PageHeader
        title="📚 知识库"
        description="导入文档，让 AI 学习你的知识"
        extra={
          <Space>
            <Segmented
              options={[
                { label: '文档', value: 'docs' },
                { label: '回收站', value: 'recycle' },
              ]}
              value={showRecycle ? 'recycle' : 'docs'}
              onChange={(val) => {
                if ((val === 'recycle') !== showRecycle) toggleRecycle()
              }}
            />
            <DocumentUpload onUpload={handleUpload} />
            <ExportButton onExport={handleExport} />
          </Space>
        }
      />

      {!showRecycle && (
        <>
          <div className={styles.statsBar}>
            <div className={styles.statCard}>
              <div className={`${styles.statIcon} ${styles.statIconPrimary}`}>
                <DatabaseOutlined />
              </div>
              <div>
                <div className={styles.statValue}>{stats.total}</div>
                <div className={styles.statLabel}>文档总数</div>
              </div>
            </div>
            <div className={styles.statCard}>
              <div className={`${styles.statIcon} ${styles.statIconSuccess}`}>
                <AppstoreOutlined />
              </div>
              <div>
                <div className={styles.statValue}>{stats.totalChunks}</div>
                <div className={styles.statLabel}>分块总数</div>
              </div>
            </div>
            <div className={styles.statCard}>
              <div className={`${styles.statIcon} ${styles.statIconWarning}`}>
                <FileTextOutlined />
              </div>
              <div>
                <div className={styles.statValue}>{stats.readyCount}</div>
                <div className={styles.statLabel}>已就绪</div>
              </div>
            </div>
          </div>
        </>
      )}

      {showRecycle ? (
        <RecycleBin
          documents={documents}
          loading={loading}
          total={total}
          page={page}
          pageSize={pageSize}
          onPageChange={handlePageChange}
          onRestore={handleRestore}
        />
      ) : !loading && documents.length === 0 ? (
        <div className={styles.emptyWrapper}>
          <EmptyState icon="📚" description="导入文档，让 AI 学习你的知识" />
        </div>
      ) : (
        <DocumentList
          documents={documents}
          loading={loading}
          total={total}
          page={page}
          pageSize={pageSize}
          onPageChange={handlePageChange}
          onViewChunks={handleViewChunks}
          onDelete={handleDelete}
        />
      )}

      <DocumentDetail
        open={activeDocId !== null}
        documentId={activeDocId}
        chunks={chunks}
        loading={chunksLoading}
        onClose={handleCloseChunks}
      />
    </div>
  )
}
