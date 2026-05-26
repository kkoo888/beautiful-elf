import { Layout, Menu } from 'antd'
import {
  MessageOutlined,
  CalendarOutlined,
  CopyOutlined,
  CodeOutlined,
  BookOutlined,
  BrainOutlined,
  TranslationOutlined,
  ToolOutlined,
  BranchesOutlined,
  RobotOutlined,
  DashboardOutlined,
  SettingOutlined,
  BellOutlined,
  PawPrintOutlined
} from '@ant-design/icons'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAppStore } from '@/stores/useAppStore'
import { useNotificationStore } from '@/stores/useNotificationStore'

const { Sider } = Layout

const menuItems = [
  {
    key: 'core',
    label: '核心',
    type: 'group' as const,
    children: [
      { key: '/', icon: <MessageOutlined />, label: '对话' },
      { key: '/schedule', icon: <CalendarOutlined />, label: '日程' },
      { key: '/clipboard', icon: <CopyOutlined />, label: '剪贴板' },
      { key: '/snippets', icon: <CodeOutlined />, label: '代码片段' }
    ]
  },
  {
    key: 'knowledge',
    label: '知识 & AI',
    type: 'group' as const,
    children: [
      { key: '/knowledge', icon: <BookOutlined />, label: '知识库' },
      { key: '/memory', icon: <BrainOutlined />, label: '记忆' },
      { key: '/translate', icon: <TranslationOutlined />, label: '翻译' },
      { key: '/skills', icon: <ToolOutlined />, label: '技能' }
    ]
  },
  {
    key: 'automation',
    label: '自动化',
    type: 'group' as const,
    children: [
      { key: '/workflow', icon: <BranchesOutlined />, label: '工作流' },
      { key: '/subagent', icon: <RobotOutlined />, label: '子代理' },
      { key: '/tools', icon: <DashboardOutlined />, label: '工具管理' }
    ]
  },
  {
    key: 'system',
    label: '系统',
    type: 'group' as const,
    children: [
      { key: '/pet', icon: <PawPrintOutlined />, label: '宠物' },
      { key: '/performance', icon: <DashboardOutlined />, label: '性能监控' },
      { key: '/notification', icon: <BellOutlined />, label: '通知' },
      { key: '/settings', icon: <SettingOutlined />, label: '设置' }
    ]
  }
]

export function Sidebar() {
  const collapsed = useAppStore((state) => state.sidebarCollapsed)
  const navigate = useNavigate()
  const location = useLocation()
  const unreadCount = useNotificationStore((state) => state.unreadCount)

  const handleMenuClick = ({ key }: { key: string }) => {
    navigate(key)
  }

  return (
    <Sider
      collapsible
      collapsed={collapsed}
      width={200}
      style={{
        height: '100vh',
        borderRight: '1px solid var(--ant-color-border-secondary)'
      }}
    >
      <div
        style={{
          height: 64,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: collapsed ? 16 : 20,
          fontWeight: 'bold',
          color: 'var(--ant-color-primary)'
        }}
      >
        {collapsed ? 'BE' : 'Beautiful-Elf'}
      </div>
      <Menu
        mode="inline"
        selectedKeys={[location.pathname]}
        items={menuItems}
        onClick={handleMenuClick}
        style={{ borderRight: 0 }}
      />
    </Sider>
  )
}
