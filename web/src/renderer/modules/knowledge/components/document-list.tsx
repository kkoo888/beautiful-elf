import { Table, Tag, Space, Button, Tooltip } from 'antd'
import { EyeOutlined, DeleteOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import type { KnowledgeDocument } from '../types/knowledge'
import { FILE_TYPE_ICONS } from '../types/knowledge'
import { confirmDanger } from '@/components/confirm-dialog'
import styles from './knowledge-panel.module.css'

interface DocumentListProps {
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
  /** 页码变化 */
  onPageChange: (page: number, pageSize: number) => void
  /** 查看分块 */
  onViewChunks: (id: string) => void
  /** 删除文档 */
  onDelete: (id: string) => void
}

/** 状态标签颜色 */
const STATUS_CONFIG: Record<KnowledgeDocument['status'], { color: string; label: string }> = {
  ready: { color: 'success', label: '就绪' },
  indexing: { color: 'processing', label: '索引中' },
  error: { color: 'error', label: '错误' },
}

/**
 * 文档列表
 * Ant Design Table 展示已导入文档
 */
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
      `确定将 "${record.fileName}" 移入回收站吗？`
    )
    if (confirmed) {
      onDelete(record.id)
    }
  }

  const columns: ColumnsType<KnowledgeDocument> = [
    {
      title: '文件名',
      dataIndex: 'fileName',
      key: 'fileName',
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
      title: '分块数',
      dataIndex: 'chunkCount',
      key: 'chunkCount',
      width: 80,
      align: 'center',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: KnowledgeDocument['status']) => {
        const config = STATUS_CONFIG[status]
        return (
          <span className={styles.statusTag}>
            <span
              className={`${styles.statusDot} ${styles[`statusDot${status.charAt(0).toUpperCase() + status.slice(1)}`]}`}
            />
            <Tag color={config.color}>{config.label}</Tag>
          </span>
        )
      },
    },
    {
      title: '导入时间',
      dataIndex: 'createdAt',
      key: 'createdAt',
      width: 170,
      render: (v: string) => new Date(v).toLocaleString('zh-CN'),
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
              disabled={record.status !== 'ready'}
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
