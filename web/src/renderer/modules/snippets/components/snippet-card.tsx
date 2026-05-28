import { useMemo } from 'react'
import { Card, Tag, Typography, Space, Button, Tooltip, Popconfirm } from 'antd'
import { CopyOutlined, EditOutlined, DeleteOutlined, FireOutlined } from '@ant-design/icons'
import { getTagColor, type Snippet } from '../types/snippets'
import styles from './snippets-panel.module.css'

const { Text } = Typography

interface SnippetCardProps {
  snippet: Snippet
  onEdit: (snippet: Snippet) => void
  onDelete: (id: string) => void
  onCopy: (snippet: Snippet) => void
}

/** 代码预览：前 5 行 + 行号 */
function CodePreview({ content }: { content: string }) {
  const lines = useMemo(() => {
    return content.split('\n').slice(0, 5)
  }, [content])

  return (
    <div className={styles.codePreview}>
      {lines.map((line, i) => (
        <div key={i} className={styles.codeLine}>
          <span className={styles.lineNumber}>{i + 1}</span>
          <span className={styles.lineContent}>{line || ' '}</span>
        </div>
      ))}
      {content.split('\n').length > 5 && <div className={styles.codeMore}>...</div>}
    </div>
  )
}

export function SnippetCard({ snippet, onEdit, onDelete, onCopy }: SnippetCardProps) {
  const tagColor = (tag: string) => getTagColor(tag)

  return (
    <Card
      className={styles.snippetCard}
      hoverable
      actions={[
        <Tooltip title="复制代码" key="copy">
          <Button type="text" icon={<CopyOutlined />} onClick={() => onCopy(snippet)} />
        </Tooltip>,
        <Tooltip title="编辑" key="edit">
          <Button type="text" icon={<EditOutlined />} onClick={() => onEdit(snippet)} />
        </Tooltip>,
        <Popconfirm
          key="delete"
          title="确定删除此片段？"
          description="删除后无法恢复"
          onConfirm={() => onDelete(snippet.id)}
          okText="删除"
          cancelText="取消"
          okButtonProps={{ danger: true }}
        >
          <Tooltip title="删除">
            <Button type="text" danger icon={<DeleteOutlined />} />
          </Tooltip>
        </Popconfirm>,
      ]}
    >
      <div className={styles.cardHeader}>
        <Text strong className={styles.cardTitle} ellipsis={{ tooltip: snippet.title }}>
          {snippet.title}
        </Text>
        <Space size={4}>
          <Tag color="blue">{snippet.language}</Tag>
          {snippet.useCount > 0 && (
            <Tooltip title={`已使用 ${snippet.useCount} 次`}>
              <Tag icon={<FireOutlined />} color="orange">
                {snippet.useCount}
              </Tag>
            </Tooltip>
          )}
        </Space>
      </div>

      <CodePreview content={snippet.content} />

      {snippet.tags.length > 0 && (
        <div className={styles.cardTags}>
          {snippet.tags.map((tag) => (
            <Tag key={tag} color={tagColor(tag)}>
              {tag}
            </Tag>
          ))}
        </div>
      )}
    </Card>
  )
}
