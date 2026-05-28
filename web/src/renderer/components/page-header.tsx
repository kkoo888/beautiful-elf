import { Typography, Space, type ReactNode } from 'antd'

const { Title, Text } = Typography

interface PageHeaderProps {
  /** 页面标题 */
  title: string
  /** 页面描述 */
  description?: string
  /** 右侧操作按钮区 */
  extra?: ReactNode
}

/**
 * 页面标题栏
 * 通用组件，所有模块的页面头部统一使用
 */
export function PageHeader({ title, description, extra }: PageHeaderProps) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: 16
      }}
    >
      <div>
        <Title level={4} style={{ marginBottom: description ? 4 : 0 }}>
          {title}
        </Title>
        {description && (
          <Text type="secondary" style={{ fontSize: 13 }}>
            {description}
          </Text>
        )}
      </div>
      {extra && <Space>{extra}</Space>}
    </div>
  )
}
