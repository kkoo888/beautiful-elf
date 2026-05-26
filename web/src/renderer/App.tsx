import { ConfigProvider, theme } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { useAppStore } from '@/stores/useAppStore'
import { AppLayout } from '@/components/layout/AppLayout'
import { GlobalErrorBoundary } from '@/components/error-boundary/GlobalErrorBoundary'
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

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 30000),
      staleTime: 5 * 60 * 1000 // 5分钟
    }
  }
})

export default function App() {
  const themeMode = useAppStore((state) => state.theme)

  const algorithm =
    themeMode === 'dark' ? theme.darkAlgorithm : theme.defaultAlgorithm

  return (
    <GlobalErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <ConfigProvider locale={zhCN} theme={{ algorithm }}>
          <BrowserRouter>
            <AppLayout />
          </BrowserRouter>
        </ConfigProvider>
      </QueryClientProvider>
    </GlobalErrorBoundary>
  )
}
