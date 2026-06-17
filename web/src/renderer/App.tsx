import { useEffect, useCallback } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { App as AntdApp } from 'antd'
import { ThemeProvider } from '@/styles/theme-provider'
import { WebSocketProvider } from '@/services/websocket'
import { WS_URL } from '@shared/constants'
import { MainLayout } from '@/layouts'
import { GlobalErrorBoundary } from '@/components/error-boundary/global-error-boundary'
import { CommandPalette } from '@/components/command-palette'
import { useAppStore } from '@/stores/use-app-store'
import { useCommandStore } from '@/stores/use-command-store'
import {
  ChatPage,
  SchedulePage,
  ClipboardPage,
  SnippetsPage,
  KnowledgePage,
  MemoryPage,
  TranslatePage,
  SkillsPage,
  WorkflowPage,
  SubagentPage,
  ToolsPage,
  PetPage,
  PerformancePage,
  NotificationPage,
  SettingsPage,
  ExpertTeamPage,
  ImageGalleryPage,
} from '@/pages'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 30000),
      staleTime: 5 * 60 * 1000, // 5 分钟
    },
  },
})

export default function App() {
  const setIsOnline = useAppStore((state) => state.setIsOnline)
  const commandPaletteOpen = useCommandStore((state) => state.isOpen)
  const toggleCommandPalette = useCommandStore((state) => state.toggle)
  const closeCommandPalette = useCommandStore((state) => state.close)

  // 监听网络状态
  useEffect(() => {
    const handleOnline = () => setIsOnline(true)
    const handleOffline = () => setIsOnline(false)

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)

    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [setIsOnline])

  // 全局快捷键 Ctrl+K 唤起命令面板
  const handleGlobalKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault()
        toggleCommandPalette()
      }
    },
    [toggleCommandPalette]
  )

  useEffect(() => {
    window.addEventListener('keydown', handleGlobalKeyDown)
    return () => window.removeEventListener('keydown', handleGlobalKeyDown)
  }, [handleGlobalKeyDown])

  // 全局未捕获错误监听
  useEffect(() => {
    const handleUnhandledRejection = (event: PromiseRejectionEvent) => {
      console.error('[Unhandled Rejection]', event.reason)
    }

    window.addEventListener('unhandledrejection', handleUnhandledRejection)
    return () => window.removeEventListener('unhandledrejection', handleUnhandledRejection)
  }, [])

  return (
    <GlobalErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <WebSocketProvider config={{ url: WS_URL }}>
          <ThemeProvider>
            <AntdApp>
              <BrowserRouter>
              <Routes>
                <Route path="/" element={<MainLayout />}>
                  <Route index element={<ChatPage />} />
                  <Route path="schedule" element={<SchedulePage />} />
                  <Route path="clipboard" element={<ClipboardPage />} />
                  <Route path="snippets" element={<SnippetsPage />} />
                  <Route path="knowledge" element={<KnowledgePage />} />
                  <Route path="memory" element={<MemoryPage />} />
                  <Route path="translate" element={<TranslatePage />} />
                  <Route path="skills" element={<SkillsPage />} />
                  <Route path="workflow" element={<WorkflowPage />} />
                  <Route path="subagent" element={<SubagentPage />} />
                  <Route path="tools" element={<ToolsPage />} />
                  <Route path="pet" element={<PetPage />} />
                  <Route path="performance" element={<PerformancePage />} />
                  <Route path="notification" element={<NotificationPage />} />
                  <Route path="expert-team" element={<ExpertTeamPage />} />
                  <Route path="image-gallery" element={<ImageGalleryPage />} />
                  <Route path="settings" element={<SettingsPage />} />
                </Route>
              </Routes>

              {/* 命令面板 — 全局覆盖层 */}
              <CommandPalette open={commandPaletteOpen} onClose={closeCommandPalette} />
            </BrowserRouter>
            </AntdApp>
          </ThemeProvider>
        </WebSocketProvider>
      </QueryClientProvider>
    </GlobalErrorBoundary>
  )
}
