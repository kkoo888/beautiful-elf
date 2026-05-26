import { useState, useEffect } from 'react'
import { Layout } from 'antd'
import { Routes, Route } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { Header } from './Header'
import { StatusBar } from './StatusBar'
import { useAppStore } from '@/stores/useAppStore'
import { useTheme } from '@/hooks'
import { ChatPanel } from '@/modules/chat/ChatPanel'
import { SchedulePanel } from '@/modules/schedule/SchedulePanel'
import { ClipboardPanel } from '@/modules/clipboard/ClipboardPanel'
import { SnippetsPanel } from '@/modules/snippets/SnippetsPanel'
import { KnowledgePanel } from '@/modules/knowledge/KnowledgePanel'
import { MemoryPanel } from '@/modules/memory/MemoryPanel'
import { TranslatePanel } from '@/modules/translate/TranslatePanel'
import { SkillsPanel } from '@/modules/skills/SkillsPanel'
import { WorkflowPanel } from '@/modules/workflow/WorkflowPanel'
import { SubagentPanel } from '@/modules/subagent/SubagentPanel'
import { ToolsPanel } from '@/modules/tools/ToolsPanel'
import { PetPanel } from '@/modules/pet/PetPanel'
import { PerformancePanel } from '@/modules/performance/PerformancePanel'
import { NotificationPanel } from '@/modules/notification/NotificationPanel'
import { SettingsPanel } from '@/modules/settings/SettingsPanel'

const { Content } = Layout

export function AppLayout() {
  const sidebarCollapsed = useAppStore((state) => state.sidebarCollapsed)
  const [isMaximized, setIsMaximized] = useState(true)

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
            backgroundColor: 'var(--ant-color-bg-layout)'
          }}
        >
          <Routes>
            <Route path="/" element={<ChatPanel />} />
            <Route path="/schedule" element={<SchedulePanel />} />
            <Route path="/clipboard" element={<ClipboardPanel />} />
            <Route path="/snippets" element={<SnippetsPanel />} />
            <Route path="/knowledge" element={<KnowledgePanel />} />
            <Route path="/memory" element={<MemoryPanel />} />
            <Route path="/translate" element={<TranslatePanel />} />
            <Route path="/skills" element={<SkillsPanel />} />
            <Route path="/workflow" element={<WorkflowPanel />} />
            <Route path="/subagent" element={<SubagentPanel />} />
            <Route path="/tools" element={<ToolsPanel />} />
            <Route path="/pet" element={<PetPanel />} />
            <Route path="/performance" element={<PerformancePanel />} />
            <Route path="/notification" element={<NotificationPanel />} />
            <Route path="/settings" element={<SettingsPanel />} />
          </Routes>
        </Content>
        <StatusBar />
      </Layout>
    </Layout>
  )
}
