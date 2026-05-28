import { useState, useEffect } from 'react'
import { Layout } from 'antd'
import { Outlet } from 'react-router-dom'
import { Sidebar } from './sidebar'
import { Header } from './header'
import { StatusBar } from './status-bar'
import { useAppStore } from '@/stores/use-app-store'
import { useTheme } from '@/hooks'

const { Content } = Layout

/**
 * 全局布局组件
 * 侧边栏 + 头部 + 内容区 + 底部状态栏
 */
export function AppLayout() {
  const [isMaximized, setIsMaximized] = useState(true)

  // 初始化主题
  useTheme()

  // 监听窗口最大化状态
  useEffect(() => {
    const checkMaximized = async () => {
      if (window.electronAPI) {
        const maximized = await window.electronAPI.window.isMaximized()
        setIsMaximized(maximized)
      }
    }
    checkMaximized()
  }, [])

  return (
    <Layout style={{ height: '100vh' }}>
      <Sidebar />
      <Layout>
        <Header isMaximized={isMaximized} />
        <Content
          style={{
            padding: '16px',
            overflow: 'auto',
            backgroundColor: 'var(--ant-color-bg-layout)',
          }}
        >
          <Outlet />
        </Content>
        <StatusBar />
      </Layout>
    </Layout>
  )
}
