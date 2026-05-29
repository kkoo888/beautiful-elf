/** 记忆详情 Drawer 组件 */

import { Drawer, Typography, Tag, Space, Progress, Descriptions, Button, Popconfirm } from 'antd'
import { MessageOutlined, ClockCircleOutlined, DeleteOutlined } from '@ant-design/icons'
import { formatDate } from '@/utils'
import type { MemoryEntry } from '../types/memory'
import styles from './memory-panel.module.css'

const { Title, Text, Paragraph } = Typography

interface MemoryDetailProps {
  /** 记忆数据 */
  memory: MemoryEntry | null
  /** 是否可见 */
  open: boolean
  /** 关闭回调 */
  onClose: () => void
  /** 删除回调 */
  onDelete: (id: string) => void
}

/**
 * 记忆详情
 * Drawer 展示完整记忆内容 + 向量相似度分数
 */
export function MemoryDetail({ memory, open, onClose, onDelete }: MemoryDetailProps) {
  if (!memory) return null

  const similarityPercent = memory.similarity ? Math.round(memory.similarity * 100) : undefined

  return (
    <Drawer
      title="记忆详情"
      open={open}
      onClose={onClose}
      width={480}
      destroyOnHidden
      extra={
        <Popconfirm
          title="确定删除这条记忆？"
          description="删除后无法恢复"
          onConfirm={() => {
            onDelete(memory.id)
            onClose()
          }}
          okText="删除"
          cancelText="取消"
          okButtonProps={{ danger: true }}
        >
          <Button danger icon={<DeleteOutlined />} size="small">
            删除
          </Button>
        </Popconfirm>
      }
    >
      <div className={styles.detailContent}>
        {/* 相似度展示（搜索模式） */}
        {similarityPercent !== undefined && (
          <div className={styles.detailSection}>
            <Text className={styles.detailSectionTitle}>语义相似度</Text>
            <div className={styles.similaritySection}>
              <Progress
                percent={similarityPercent}
                strokeColor={
                  similarityPercent >= 80
                    ? '#52c41a'
                    : similarityPercent >= 60
                      ? '#faad14'
                      : '#ff4d4f'
                }
                format={(p) => `${p}%`}
                className={styles.similarityBar}
              />
            </div>
          </div>
        )}

        {/* 摘要 */}
        <div className={styles.detailSection}>
          <Text className={styles.detailSectionTitle}>摘要</Text>
          <Title level={5} style={{ margin: 0 }}>
            {memory.summary}
          </Title>
        </div>

        {/* 完整内容 */}
        <div className={styles.detailSection}>
          <Text className={styles.detailSectionTitle}>完整内容</Text>
          <Paragraph className={styles.detailText}>{memory.content}</Paragraph>
        </div>

        {/* 元信息 */}
        <div className={styles.detailSection}>
          <Text className={styles.detailSectionTitle}>信息</Text>
          <Descriptions column={1} size="small" bordered>
            <Descriptions.Item
              label={
                <>
                  <MessageOutlined /> 来源会话
                </>
              }
            >
              {memory.conversationId}
            </Descriptions.Item>
            <Descriptions.Item
              label={
                <>
                  <ClockCircleOutlined /> 创建时间
                </>
              }
            >
              {formatDate(memory.createdAt)}
            </Descriptions.Item>
          </Descriptions>
        </div>

        {/* 标签 */}
        {memory.tags.length > 0 && (
          <div className={styles.detailSection}>
            <Text className={styles.detailSectionTitle}>标签</Text>
            <Space size={[4, 4]} wrap>
              {memory.tags.map((tag) => (
                <Tag key={tag} color="blue">
                  {tag}
                </Tag>
              ))}
            </Space>
          </div>
        )}
      </div>
    </Drawer>
  )
}
