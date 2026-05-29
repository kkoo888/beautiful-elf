import { Drawer, Spin, Empty, Typography } from 'antd'
import type { KnowledgeChunk } from '../types/knowledge'
import styles from './knowledge-panel.module.css'

const { Text } = Typography

interface DocumentDetailProps {
  /** 是否可见 */
  open: boolean
  /** 文档ID */
  documentId: string | null
  /** 分块数据 */
  chunks: KnowledgeChunk[]
  /** 加载中 */
  loading: boolean
  /** 关闭回调 */
  onClose: () => void
}

/**
 * 文档详情抽屉
 * 展示文档的分块内容预览
 */
export function DocumentDetail({
  open,
  documentId,
  chunks,
  loading,
  onClose,
}: DocumentDetailProps) {
  return (
    <Drawer title="📄 文档分块预览" open={open} onClose={onClose} width={520} destroyOnClose>
      {loading ? (
        <div style={{ textAlign: 'center', padding: '48px 0' }}>
          <Spin tip="加载分块中..." />
        </div>
      ) : chunks.length === 0 ? (
        <Empty description="暂无分块数据" />
      ) : (
        <div>
          <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
            共 {chunks.length} 个分块
          </Text>
          {chunks.map((chunk) => (
            <div key={chunk.id} className={styles.chunkCard}>
              <span className={styles.chunkIndex}>#{chunk.chunkIndex + 1}</span>
              <div className={styles.chunkContent}>{chunk.content}</div>
            </div>
          ))}
        </div>
      )}
    </Drawer>
  )
}
