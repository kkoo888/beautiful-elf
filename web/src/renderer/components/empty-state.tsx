import { Empty, Button, Typography, Space, type EmptyProps } from 'antd'
import type { ReactNode } from 'react'

const { Text } = Typography

interface EmptyStateProps {
  /** 图标或图片 */
  icon?: ReactNode
  /** 提示文字 */
  description?: string
  /** 操作按钮文字 */
  actionText?: string
  /** 操作按钮点击回调 */
  onAction?: () => void
  /** 自定义子内容 */
  children?: ReactNode
  /** Ant Design Empty 的 image 属性 */
  image?: EmptyProps['image']
}

/**
 * 空状态占位组件
 * 通用组件，用于列表为空、无数据等场景
 */
export function EmptyState({
  icon,
  description = '暂无数据',
  actionText,
  onAction,
  children,
  image,
}: EmptyStateProps) {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '48px 24px',
        textAlign: 'center',
      }}
    >
      <Empty
        image={image || Empty.PRESENTED_IMAGE_SIMPLE}
        description={
          <Space orientation="vertical" size={4}>
            {icon && <span style={{ fontSize: 32 }}>{icon}</span>}
            <Text type="secondary">{description}</Text>
          </Space>
        }
      >
        {actionText && onAction && (
          <Button type="primary" onClick={onAction}>
            {actionText}
          </Button>
        )}
        {children}
      </Empty>
    </div>
  )
}
