import { Layout, Space, Typography, Badge } from 'antd'
import { useAppStore } from '@/stores/use-app-store'

const { Footer } = Layout
const { Text } = Typography

/**
 * 底部状态栏组件
 * 显示网络状态 + 版本信息
 */
export function StatusBar() {
  const isOnline = useAppStore((state) => state.isOnline)

  return (
    <Footer
      style={{
        padding: '4px 16px',
        height: 28,
        lineHeight: '20px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        borderTop: '1px solid var(--ant-color-border-secondary)',
        backgroundColor: 'var(--ant-color-bg-container)',
        fontSize: 12,
      }}
    >
      <Space size="small">
        {isOnline ? (
          <Badge status="success" text={<Text type="secondary">在线</Text>} />
        ) : (
          <Badge status="error" text={<Text type="danger">离线</Text>} />
        )}
      </Space>

      <Space size="small">
        <Text type="secondary" style={{ fontSize: 12 }}>
          Beautiful-Elf v0.1.0
        </Text>
      </Space>
    </Footer>
  )
}
