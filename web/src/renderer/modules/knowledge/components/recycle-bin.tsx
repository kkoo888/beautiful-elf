import { Table, Tag, Space, Button, Tooltip } from 'antd'
import { UndoOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import type { KnowledgeDocument } from '@/types'
import { FILE_TYPE_ICONS } from '../types/knowledge'
import { EmptyState } from '@/components/empty-state'

interface RecycleBinProps {
  documents: KnowledgeDocument[]
  loading: boolean
  total: number
  page: number
  pageSize: number
  onPageChange: (page: number, pageSize: number) => void
  onRestore: (id: number) => void
}

export function RecycleBin({
  documents,
  loading,
  total,
  page,
  pageSize,
  onPageChange,
  onRestore,
}: RecycleBinProps) {
  const columns: ColumnsType<KnowledgeDocument> = [
    {
      title: '文件名',
      dataIndex: 'filename',
      key: 'filename',
      ellipsis: true,
      render: (name: string, record: KnowledgeDocument) => (
        <Space size={8}>
          <span>{FILE_TYPE_ICONS[record.fileType] ?? '📄'}</span>
          <span>{name}</span>
        </Space>
      ),
    },
    {
      title: '类型',
      dataIndex: 'fileType',
      key: 'fileType',
      width: 80,
      render: (type: string) => <Tag>{type.toUpperCase()}</Tag>,
    },
    {
      title: '删除时间',
      dataIndex: 'updatedAt',
      key: 'updatedAt',
      width: 170,
      render: (v: string) => new Date(v).toLocaleString('zh-CN'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 80,
      render: (_, record) => (
        <Tooltip title="恢复文档">
          <Button
            type="text"
            size="small"
            icon={<UndoOutlined />}
            onClick={() => onRestore(record.id)}
          >
            恢复
          </Button>
        </Tooltip>
      ),
    },
  ]

  if (!loading && documents.length === 0) {
    return <EmptyState icon="🗑️" description="回收站是空的" />
  }

  return (
    <Table<KnowledgeDocument>
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
