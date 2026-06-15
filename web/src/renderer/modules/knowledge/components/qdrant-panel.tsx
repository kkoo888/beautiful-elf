import {
  Table,
  Button,
  Tag,
  Popconfirm,
  Drawer,
  Space,
  Typography,
  Spin,
} from 'antd'
import {
  DeleteOutlined,
  EyeOutlined,
  ReloadOutlined,
  ApiOutlined,
  DatabaseOutlined,
  ClusterOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { useQdrant } from '../hooks/use-qdrant'
import type {
  DocumentVectorCount,
  QdrantVectorRecord,
} from '../services/knowledge-api'
import styles from './knowledge-panel.module.css'

const { Text } = Typography

function statusColor(status: string): string {
  if (status === 'green') return 'success'
  if (status === 'yellow') return 'warning'
  return 'error'
}

/**
 * Qdrant 向量库管理面板
 */
export function QdrantPanel() {
  const {
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
  } = useQdrant()

  const handleRefresh = () => {
    loadStats()
    loadDocCounts()
  }

  // ── 统计卡片 ──────────────────────────────────────────
  const statsCards = (
    <div className={styles.statsBar}>
      <div className={styles.statCard}>
        <div className={`${styles.statIcon} ${styles.statIconPrimary}`}>
          <ApiOutlined />
        </div>
        <div>
          <div className={styles.statValue}>
            {statsLoading ? <Spin size="small" /> : stats?.isConnected ? '已连接' : '未连接'}
          </div>
          <div className={styles.statLabel}>Qdrant 状态</div>
        </div>
      </div>

      <div className={styles.statCard}>
        <div className={`${styles.statIcon} ${styles.statIconSuccess}`}>
          <ClusterOutlined />
        </div>
        <div>
          <div className={styles.statValue}>
            {statsLoading ? <Spin size="small" /> : stats?.collectionName ?? '-'}
          </div>
          <div className={styles.statLabel}>集合名称</div>
        </div>
      </div>

      <div className={styles.statCard}>
        <div className={`${styles.statIcon} ${styles.statIconWarning}`}>
          <DatabaseOutlined />
        </div>
        <div>
          <div className={styles.statValue}>
            {statsLoading ? <Spin size="small" /> : (stats?.vectorCount ?? 0).toLocaleString()}
          </div>
          <div className={styles.statLabel}>向量总数</div>
        </div>
      </div>

      <div className={styles.statCard}>
        <div className={`${styles.statIcon} ${styles.statIconPrimary}`}>
          <Tag
            color={stats?.status ? statusColor(stats.status) : 'default'}
            style={{ margin: 0, fontSize: 12 }}
          >
            {stats?.status?.toUpperCase() ?? '—'}
          </Tag>
        </div>
        <div>
          <div className={styles.statValue} style={{ fontSize: 16 }}>
            {stats?.status ?? 'unknown'}
          </div>
          <div className={styles.statLabel}>集合健康度</div>
        </div>
      </div>
    </div>
  )

  // ── 文档向量计数列表列 ─────────────────────────────────
  const docCountColumns: ColumnsType<DocumentVectorCount> = [
    {
      title: '文档 ID',
      dataIndex: 'documentId',
      width: 100,
      sorter: (a, b) => a.documentId - b.documentId,
    },
    {
      title: '文件名',
      dataIndex: 'filename',
      ellipsis: true,
    },
    {
      title: '向量数',
      dataIndex: 'vectorCount',
      width: 100,
      sorter: (a, b) => a.vectorCount - b.vectorCount,
      defaultSortOrder: 'descend',
      render: (v: number) => <Text strong>{v.toLocaleString()}</Text>,
    },
    {
      title: '操作',
      key: 'actions',
      width: 160,
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => selectDocument(record.documentId)}
          >
            查看向量
          </Button>
          <Popconfirm
            title="删除该文档的所有向量？"
            description="此操作不可撤销，Qdrant 中该文档的向量将被永久删除"
            onConfirm={() => handleDeleteDocVectors(record.documentId)}
            okText="确认删除"
            cancelText="取消"
            okButtonProps={{ danger: true }}
          >
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>
              清空
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  // ── 向量详情列 ─────────────────────────────────────────
  const vectorColumns: ColumnsType<QdrantVectorRecord> = [
    {
      title: 'Point ID',
      dataIndex: 'pointId',
      width: 280,
      ellipsis: true,
      render: (id: string) => (
        <Text copyable={{ text: id }} style={{ fontFamily: 'monospace', fontSize: 12 }}>
          {id}
        </Text>
      ),
    },
    {
      title: 'Chunk ID',
      dataIndex: 'chunkId',
      width: 200,
      ellipsis: true,
      render: (id: string) => (
        <Text style={{ fontFamily: 'monospace', fontSize: 12 }}>{id || '—'}</Text>
      ),
    },
    {
      title: '内容预览',
      dataIndex: 'contentPreview',
      ellipsis: true,
      render: (text: string) => (
        <Text
          ellipsis={{ tooltip: text.slice(0, 500) }}
          style={{ fontSize: 12, color: 'var(--ant-color-text-secondary)' }}
        >
          {text || '—'}
        </Text>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 80,
      render: (_, record) => (
        <Popconfirm
          title="删除此向量？"
          onConfirm={() => handleDeleteVector(activeDocId!, record.pointId)}
          okText="确认"
          cancelText="取消"
          okButtonProps={{ danger: true }}
        >
          <Button type="link" size="small" danger icon={<DeleteOutlined />} />
        </Popconfirm>
      ),
    },
  ]

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* 刷新按钮 */}
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 12 }}>
        <Button icon={<ReloadOutlined />} onClick={handleRefresh} loading={statsLoading || docCountsLoading}>
          刷新
        </Button>
      </div>

      {/* 统计卡片 */}
      {statsCards}

      {/* 文档向量列表 */}
      <div style={{ flex: 1, overflow: 'auto', marginTop: 8 }}>
        <Table<DocumentVectorCount>
          rowKey="documentId"
          columns={docCountColumns}
          dataSource={docCounts}
          loading={docCountsLoading}
          pagination={{ pageSize: 10, showTotal: (t) => `共 ${t} 个文档`, showSizeChanger: false }}
          size="small"
          locale={{ emptyText: '暂无向量数据（请先上传文档并等待向量化完成）' }}
        />
      </div>

      {/* 向量详情 Drawer */}
      <Drawer
        title={
          activeDocId !== null
            ? `文档 #${activeDocId} 的向量（${docCounts.find((d) => d.documentId === activeDocId)?.vectorCount ?? '?'} 个）`
            : '向量详情'
        }
        open={activeDocId !== null}
        onClose={handleCloseVectors}
        size={900}
        destroyOnHidden
      >
        <Table<QdrantVectorRecord>
          rowKey="pointId"
          columns={vectorColumns}
          dataSource={vectors}
          loading={vectorsLoading}
          pagination={false}
          size="small"
          scroll={{ y: 'calc(100vh - 280px)' }}
          locale={{ emptyText: '暂无向量' }}
        />
        {vectorsNextOffset !== null && (
          <div style={{ textAlign: 'center', marginTop: 12 }}>
            <Button loading={vectorsLoading} onClick={loadMoreVectors}>
              加载更多
            </Button>
          </div>
        )}
      </Drawer>
    </div>
  )
}
