import { Input, Select, Segmented, Space } from 'antd'
import { SearchOutlined } from '@ant-design/icons'
import { PageHeader } from '@/components/page-header'
import { EmptyState } from '@/components/empty-state'
import { useKnowledge } from '../hooks/use-knowledge'
import { DocumentUpload } from './document-upload'
import { DocumentList } from './document-list'
import { DocumentDetail } from './document-detail'
import { RecycleBin } from './recycle-bin'
import { ExportButton } from './export-button'
import type { KnowledgeFileType } from '../types/knowledge'
import styles from './knowledge-panel.module.css'

const { Search } = Input

const FILE_TYPE_OPTIONS = [
  { label: '全部类型', value: '' },
  { label: 'PDF', value: 'pdf' },
  { label: 'DOCX', value: 'docx' },
  { label: 'Markdown', value: 'md' },
  { label: 'TXT', value: 'txt' },
  { label: 'JSON', value: 'json' },
  { label: 'CSV', value: 'csv' },
  { label: 'YAML', value: 'yaml' },
  { label: 'HTML', value: 'html' },
  { label: 'XML', value: 'xml' },
  { label: 'ZIP', value: 'zip' },
]

/**
 * 知识库主面板
 * 包含文档上传、文档列表、回收站、分块预览、导出
 */
export function KnowledgePanel() {
  const {
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
    handleUpload,
    handleDelete,
    handleRestore,
    handleViewChunks,
    handleCloseChunks,
    handleExport,
  } = useKnowledge()

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
            <ExportButton onExport={handleExport} />
          </Space>
        }
      />

      {!showRecycle && (
        <>
          <DocumentUpload onUpload={handleUpload} />

          <div className={styles.toolbar}>
            <Search
              className={styles.searchInput}
              placeholder="搜索文档名称..."
              allowClear
              enterButton={<SearchOutlined />}
              onSearch={setKeyword}
              onChange={(e) => {
                if (!e.target.value) setKeyword('')
              }}
            />
            <Select
              className={styles.typeSelect}
              options={FILE_TYPE_OPTIONS}
              value={fileType ?? ''}
              onChange={(val) => setFileType(val ? (val as KnowledgeFileType) : undefined)}
              placeholder="文件类型"
            />
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
        <EmptyState icon="📚" description="导入文档，让 AI 学习你的知识" />
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
