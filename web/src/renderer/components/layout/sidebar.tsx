import { Layout, Menu, Tooltip } from 'antd'
import {
  MessageOutlined,
  CalendarOutlined,
  CopyOutlined,
  CodeOutlined,
  BookOutlined,
  BulbOutlined,
  TranslationOutlined,
  ToolOutlined,
  BranchesOutlined,
  RobotOutlined,
  DashboardOutlined,
  SettingOutlined,
  BellOutlined,
  HeartOutlined,
  TeamOutlined,
  PictureOutlined,
  PlayCircleOutlined,
  ExperimentOutlined,
} from '@ant-design/icons'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAppStore } from '@/stores/use-app-store'
import { useMediaQuery } from '@/hooks/use-media-query'
import type { ItemType } from 'antd/es/menu/interface'

const { Sider } = Layout

/** 响应式断点 */
const COLLAPSE_BREAKPOINT = 900

/** 侧边栏菜单配置 — 按分组折叠 */
const menuItems: ItemType[] = [
  {
    key: 'core',
    label: '核心',
    type: 'group' as const,
    children: [
      { key: '/', icon: <MessageOutlined />, label: '对话' },
      { key: '/schedule', icon: <CalendarOutlined />, label: '日程' },
      { key: '/clipboard', icon: <CopyOutlined />, label: '剪贴板' },
      { key: '/snippets', icon: <CodeOutlined />, label: '代码片段' },
    ],
  },
  {
    key: 'knowledge',
    label: '知识 & AI',
    type: 'group' as const,
    children: [
      { key: '/knowledge', icon: <BookOutlined />, label: '知识库' },
      { key: '/memory', icon: <BulbOutlined />, label: '记忆' },
      { key: '/translate', icon: <TranslationOutlined />, label: '翻译' },
      { key: '/skills', icon: <ToolOutlined />, label: '技能' },
      { key: '/image-gallery', icon: <PictureOutlined />, label: '图片画廊' },
      { key: '/video-gallery', icon: <PlayCircleOutlined />, label: '视频画廊' },
      { key: '/intent-learning', icon: <ExperimentOutlined />, label: '意图学习' },
    ],
  },
  {
    key: 'automation',
    label: '自动化',
    type: 'group' as const,
    children: [
      { key: '/workflow', icon: <BranchesOutlined />, label: '工作流' },
      { key: '/expert-team', icon: <TeamOutlined />, label: '专家团' },
      { key: '/subagent', icon: <RobotOutlined />, label: '子代理' },
      { key: '/tools', icon: <DashboardOutlined />, label: '工具管理' },
    ],
  },
  {
    key: 'system',
    label: '系统',
    type: 'group' as const,
    children: [
      { key: '/pet', icon: <HeartOutlined />, label: '宠物' },
      { key: '/performance', icon: <DashboardOutlined />, label: '性能监控' },
      { key: '/notification', icon: <BellOutlined />, label: '通知' },
      { key: '/settings', icon: <SettingOutlined />, label: '设置' },
    ],
  },
]

/**
 * 侧边栏导航组件
 * - 响应式折叠：窗口 < 900px 自动收起
 * - 折叠状态持久化到 localStorage（via zustand persist）
 * - 菜单分组：核心 / 知识&AI / 自动化 / 系统
 */
export function Sidebar() {
  const collapsed = useAppStore((state) => state.sidebarCollapsed)
  const setSidebarCollapsed = useAppStore((state) => state.setSidebarCollapsed)
  const navigate = useNavigate()
  const location = useLocation()
  const isNarrow = useMediaQuery(`(max-width: ${COLLAPSE_BREAKPOINT - 1}px)`)

  // 窄屏自动折叠
  const effectiveCollapsed = isNarrow || collapsed

  const handleCollapse = (value: boolean) => {
    setSidebarCollapsed(value)
  }

  const handleMenuClick = ({ key }: { key: string }) => {
    navigate(key)
  }

  return (
    <Sider
      collapsible
      collapsed={effectiveCollapsed}
      onCollapse={handleCollapse}
      width={200}
      collapsedWidth={64}
      breakpoint="lg"
      trigger={null}
      style={{
        height: '100vh',
        borderRight: '1px solid var(--ant-color-border-secondary)',
        overflow: 'auto',
      }}
    >
      {/* Logo 区域 */}
      <Tooltip title={effectiveCollapsed ? 'Beautiful-Elf' : ''} placement="right">
        <div
          style={{
            height: 64,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: effectiveCollapsed ? 16 : 20,
            fontWeight: 'bold',
            color: 'var(--ant-color-primary)',
            cursor: 'pointer',
            userSelect: 'none',
          }}
          onClick={() => handleCollapse(!effectiveCollapsed)}
        >
          {effectiveCollapsed ? 'BE' : 'Beautiful-Elf'}
        </div>
      </Tooltip>

      {/* 导航菜单 */}
      <Menu
        mode="inline"
        selectedKeys={[location.pathname]}
        items={menuItems}
        onClick={handleMenuClick}
        inlineCollapsed={effectiveCollapsed}
        style={{ borderRight: 0 }}
      />
    </Sider>
  )
}
