import { Drawer, Spin, Empty, Typography, Badge } from 'antd'
import { AppstoreOutlined } from '@ant-design/icons'
import type { KnowledgeChunk } from '../services/knowledge-api'
import styles from './knowledge-panel.module.css'

const { Text } = Typography

interface DocumentDetailProps {
  open: boolean
  documentId: number | null
  chunks: KnowledgeChunk[]
  loading: boolean
  onClose: () => void
}

export function DocumentDetail({
  open,
  documentId,
  chunks,
  loading,
  onClose,
}: DocumentDetailProps) {
  return (
    <Drawer
      title={
        <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <AppstoreOutlined />
          文档分块预览
        </span>
      }
      open={open}
      onClose={onClose}
      width={520}
      destroyOnHidden
    >
      {loading ? (
        <div style={{ textAlign: 'center', padding: '64px 0' }}>
          <Spin tip="加载分块中..." size="large" />
        </div>
      ) : chunks.length === 0 ? (
        <div className={styles.emptyWrapper}>
          <Empty description="暂无分块数据" />
        </div>
      ) : (
        <div>
          <Text type="secondary" style={{ display: 'block', marginBottom: 20, fontSize: 13 }}>
            共 <Text strong>{chunks.length}</Text> 个分块
          </Text>
          {chunks.map((chunk) => (
            <div key={chunk.id} className={styles.chunkCard}>
              <Badge
                count={`#${chunk.chunkIndex + 1}`}
                style={{
                  backgroundColor: '#e6f4ff',
                  color: '#1677ff',
                  fontSize: 12,
                  fontWeight: 600,
                  boxShadow: 'none',
                }}
              />
              <div className={styles.chunkContent} style={{ marginTop: 8 }}>
                {chunk.contentPreview}
              </div>
            </div>
          ))}
        </div>
      )}
    </Drawer>
  )
}
