import { Table, Tag, Space, Button, Tooltip } from 'antd'
import { EyeOutlined, DeleteOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import type { KnowledgeDocument } from '@/types'
import { FILE_TYPE_ICONS, STATUS_MAP } from '../types/knowledge'
import { confirmDanger } from '@/components/confirm-dialog'
import styles from './knowledge-panel.module.css'

interface DocumentListProps {
  documents: KnowledgeDocument[]
  loading: boolean
  total: number
  page: number
  pageSize: number
  onPageChange: (page: number, pageSize: number) => void
  onViewChunks: (id: number) => void
  onDelete: (id: number) => void
}

function formatFileSize(bytes: number): string {
  if (!bytes) return '-'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

export function DocumentList({
  documents,
  loading,
  total,
  page,
  pageSize,
  onPageChange,
  onViewChunks,
  onDelete,
}: DocumentListProps) {
  const handleDelete = async (record: KnowledgeDocument) => {
    const confirmed = await confirmDanger(
      '移入回收站',
      `确定将 "${record.filename}" 移入回收站吗？`
    )
    if (confirmed) {
      onDelete(record.id)
    }
  }

  const columns: ColumnsType<KnowledgeDocument> = [
    {
      title: '文件名',
      dataIndex: 'filename',
      key: 'filename',
      ellipsis: true,
      render: (name: string, record: KnowledgeDocument) => (
        <div className={styles.fileName}>
          <span className={styles.fileIcon}>
            {FILE_TYPE_ICONS[record.fileType] ?? '📄'}
          </span>
          <span className={styles.fileNameText}>{name}</span>
        </div>
      ),
    },
    {
      title: '类型',
      dataIndex: 'fileType',
      key: 'fileType',
      width: 90,
      render: (type: string) => (
        <Tag color="blue" style={{ borderRadius: 4 }}>
          {type.toUpperCase()}
        </Tag>
      ),
    },
    {
      title: '大小',
      dataIndex: 'fileSize',
      key: 'fileSize',
      width: 100,
      render: (size: number) => (
        <span style={{ color: 'var(--ant-color-text-secondary)', fontSize: 13 }}>
          {formatFileSize(size)}
        </span>
      ),
    },
    {
      title: '分块数',
      dataIndex: 'chunkCount',
      key: 'chunkCount',
      width: 90,
      align: 'center',
      render: (count: number) => <span style={{ fontWeight: 500 }}>{count}</span>,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 110,
      render: (status: number) => {
        const config = STATUS_MAP[status] ?? { label: '未知', color: 'default' }
        return (
          <Tag color={config.color} style={{ borderRadius: 4, margin: 0 }}>
            {config.label}
          </Tag>
        )
      },
    },
    {
      title: '导入时间',
      dataIndex: 'createdAt',
      key: 'createdAt',
      width: 160,
      render: (v: string) => (
        <span style={{ fontSize: 13, color: 'var(--ant-color-text-secondary)' }}>
          {new Date(v).toLocaleString('zh-CN')}
        </span>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 100,
      render: (_, record) => (
        <Space size={4}>
          <Tooltip title="查看分块">
            <Button
              type="text"
              size="small"
              icon={<EyeOutlined />}
              onClick={() => onViewChunks(record.id)}
              disabled={record.status !== 2}
            />
          </Tooltip>
          <Tooltip title="移入回收站">
            <Button
              type="text"
              size="small"
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDelete(record)}
            />
          </Tooltip>
        </Space>
      ),
    },
  ]

  return (
    <Table<KnowledgeDocument>
      className={styles.tableWrapper}
      columns={columns}
      dataSource={documents}
      rowKey="id"
      loading={loading}
      size="middle"
      pagination={{
        current: page,
        pageSize,
        total,
        showSizeChanger: true,
        showTotal: (t) => `共 ${t} 个文档`,
        onChange: onPageChange,
      }}
    />
  )
}
