import { Drawer, Tag, Typography, Button, Space, Tooltip } from 'antd'
import { CopyOutlined, PushpinOutlined, DeleteOutlined } from '@ant-design/icons'
import { formatDate } from '@/utils'
import type { ClipboardItem } from '../types/clipboard'
import {
  getContentTypeIcon,
  getContentTypeLabel
} from '../hooks/use-clipboard'
import styles from './clipboard-panel.module.css'

const { Text, Paragraph } = Typography

interface ClipboardDetailProps {
  item: ClipboardItem | null
  onClose: () => void
  onCopy: (item: ClipboardItem) => void
  onTogglePin: (id: string) => void
  onDelete: (id: string) => void
}

/**
 * 剪贴板内容详情抽屉
 * 展示完整内容，支持代码语法高亮（简单方案：pre + code）
 */
export function ClipboardDetail({
  item,
  onClose,
  onCopy,
  onTogglePin,
  onDelete
}: ClipboardDetailProps) {
  if (!item) return null

  const icon = getContentTypeIcon(item.contentType)
  const typeLabel = getContentTypeLabel(item.contentType)
  const isCode = item.contentType === 'code'

  return (
    <Drawer
      title={
        <Space>
          <span>{icon}</span>
          <span>内容详情</span>
          <Tag color="blue">{typeLabel}</Tag>
          {item.language && <Tag>{item.language}</Tag>}
        </Space>
      }
      open={!!item}
      onClose={onClose}
      width={480}
      className={styles.detailDrawer}
      extra={
        <Space>
          <Tooltip title={item.isPinned ? '取消固定' : '固定'}>
            <Button
              icon={<PushpinOutlined />}
              type={item.isPinned ? 'primary' : 'default'}
              onClick={() => onTogglePin(item.id)}
            />
          </Tooltip>
          <Tooltip title="复制">
            <Button
              icon={<CopyOutlined />}
              onClick={() => onCopy(item)}
            />
          </Tooltip>
          <Tooltip title="删除">
            <Button
              icon={<DeleteOutlined />}
              danger
              onClick={() => {
                onDelete(item.id)
                onClose()
              }}
            />
          </Tooltip>
        </Space>
      }
    >
      <div className={styles.detailMeta}>
        <Text type="secondary">
          复制于 {formatDate(item.copiedAt, 'YYYY-MM-DD HH:mm:ss')}
        </Text>
        {item.isPinned && (
          <Tag color="orange" className={styles.detailPinTag}>
            📌 已固定
          </Tag>
        )}
      </div>

      <div className={styles.detailContent}>
        {isCode ? (
          <pre className={styles.codeBlock}>
            <code>{item.content}</code>
          </pre>
        ) : item.contentType === 'link' ? (
          <Paragraph>
            <a href={item.content} target="_blank" rel="noopener noreferrer">
              {item.content}
            </a>
          </Paragraph>
        ) : (
          <Paragraph className={styles.textContent}>{item.content}</Paragraph>
        )}
      </div>
    </Drawer>
  )
}
