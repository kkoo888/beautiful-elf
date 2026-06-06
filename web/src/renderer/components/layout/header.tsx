import { Layout, Space, Button, Tooltip, Badge } from 'antd'
import {
  MinusOutlined,
  CloseOutlined,
  ExpandOutlined,
  CompressOutlined,
  SearchOutlined,
  SunOutlined,
  MoonOutlined,
  BellOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { useElectronApi, useTheme } from '@/hooks'
import { useNotificationStore } from '@/stores/use-notification-store'
import { useCommandStore } from '@/stores/use-command-store'

const { Header: AntHeader } = Layout

interface HeaderProps {
  isMaximized: boolean
}

/**
 * 顶部栏组件
 * 包含：命令面板入口、主题切换、通知、窗口控制
 */
export function Header({ isMaximized }: HeaderProps) {
  const { window: windowApi } = useElectronApi()
  const { isDark, toggleTheme } = useTheme()
  const navigate = useNavigate()
  const unreadCount = useNotificationStore((state) => state.unreadCount)
  const openCommandPalette = useCommandStore((state) => state.open)

  return (
    <AntHeader
      style={{
        padding: '0 16px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        borderBottom: '1px solid var(--ant-color-border-secondary)',
        backgroundColor: 'var(--ant-color-bg-container)',
        height: 48,
        lineHeight: '48px',
      }}
    >
      {/* 左侧：搜索 */}
      <Space>
        <Tooltip title="命令面板 (Ctrl+K)">
          <Button type="text" icon={<SearchOutlined />} onClick={openCommandPalette} />
        </Tooltip>
      </Space>

      {/* 右侧：主题切换、通知、窗口控制 */}
      <Space size="small">
        <Tooltip title={isDark ? '浅色模式' : '暗色模式'}>
          <Button
            type="text"
            icon={isDark ? <SunOutlined /> : <MoonOutlined />}
            onClick={toggleTheme}
          />
        </Tooltip>

        <Tooltip title="通知">
          <Badge count={unreadCount} size="small">
            <Button type="text" icon={<BellOutlined />} onClick={() => navigate('/notification')} />
          </Badge>
        </Tooltip>

        <div style={{ width: 1, height: 20, backgroundColor: 'var(--ant-color-border)' }} />

        <Tooltip title="最小化">
          <Button type="text" icon={<MinusOutlined />} onClick={() => windowApi.minimize()} />
        </Tooltip>
        <Tooltip title={isMaximized ? '还原' : '最大化'}>
          <Button
            type="text"
            icon={isMaximized ? <CompressOutlined /> : <ExpandOutlined />}
            onClick={() => windowApi.maximize()}
          />
        </Tooltip>
        <Tooltip title="关闭">
          <Button type="text" icon={<CloseOutlined />} onClick={() => windowApi.close()} danger />
        </Tooltip>
      </Space>
    </AntHeader>
  )
}
