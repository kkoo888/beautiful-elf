import React, { Suspense, useEffect, useCallback } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ThemeProvider } from '@/styles/theme-provider'
import { AppLayout } from '@/components/layout/app-layout'
import { GlobalErrorBoundary } from '@/components/error-boundary/global-error-boundary'
import { ModuleErrorBoundary } from '@/components/error-boundary/module-error-boundary'
import { LoadingSkeleton } from '@/components/loading/loading-skeleton'
import { CommandPalette } from '@/components/command-palette'
import { useAppStore } from '@/stores/use-app-store'
import { useCommandStore } from '@/stores/use-command-store'

// 懒加载所有功能模块
const ChatPanel = React.lazy(() => import('@/modules/chat/chat-panel'))
const SchedulePanel = React.lazy(() => import('@/modules/schedule/schedule-panel'))
const ClipboardPanel = React.lazy(() => import('@/modules/clipboard/clipboard-panel'))
const SnippetsPanel = React.lazy(() => import('@/modules/snippets/snippets-panel'))
const KnowledgePanel = React.lazy(() => import('@/modules/knowledge/knowledge-panel'))
const MemoryPanel = React.lazy(() => import('@/modules/memory/memory-panel'))
const TranslatePanel = React.lazy(() => import('@/modules/translate/translate-panel'))
const SkillsPanel = React.lazy(() => import('@/modules/skills/skills-panel'))
const WorkflowPanel = React.lazy(() => import('@/modules/workflow/workflow-panel'))
const SubagentPanel = React.lazy(() => import('@/modules/subagent/subagent-panel'))
const ToolsPanel = React.lazy(() => import('@/modules/tools/tools-panel'))
const PetPanel = React.lazy(() => import('@/modules/pet/pet-panel'))
const PerformancePanel = React.lazy(() => import('@/modules/performance/performance-panel'))
const NotificationPanel = React.lazy(() => import('@/modules/notification/notification-panel'))
const SettingsPanel = React.lazy(() => import('@/modules/settings/settings-panel'))

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 30000),
      staleTime: 5 * 60 * 1000, // 5 分钟
    },
  },
})

/**
 * 模块级 Suspense 包裹器
 * 每个路由独立加载状态 + 错误边界
 */
function ModuleSuspense({
  children,
  moduleName,
}: {
  children: React.ReactNode
  moduleName: string
}) {
  return (
    <ModuleErrorBoundary moduleName={moduleName}>
      <Suspense fallback={<LoadingSkeleton type="text" rows={4} />}>{children}</Suspense>
    </ModuleErrorBoundary>
  )
}

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
        <ThemeProvider>
          <BrowserRouter>
            <Routes>
              <Route path="/" element={<AppLayout />}>
                <Route
                  index
                  element={
                    <ModuleSuspense moduleName="对话">
                      <ChatPanel />
                    </ModuleSuspense>
                  }
                />
                <Route
                  path="schedule"
                  element={
                    <ModuleSuspense moduleName="日程">
                      <SchedulePanel />
                    </ModuleSuspense>
                  }
                />
                <Route
                  path="clipboard"
                  element={
                    <ModuleSuspense moduleName="剪贴板">
                      <ClipboardPanel />
                    </ModuleSuspense>
                  }
                />
                <Route
                  path="snippets"
                  element={
                    <ModuleSuspense moduleName="代码片段">
                      <SnippetsPanel />
                    </ModuleSuspense>
                  }
                />
                <Route
                  path="knowledge"
                  element={
                    <ModuleSuspense moduleName="知识库">
                      <KnowledgePanel />
                    </ModuleSuspense>
                  }
                />
                <Route
                  path="memory"
                  element={
                    <ModuleSuspense moduleName="记忆">
                      <MemoryPanel />
                    </ModuleSuspense>
                  }
                />
                <Route
                  path="translate"
                  element={
                    <ModuleSuspense moduleName="翻译">
                      <TranslatePanel />
                    </ModuleSuspense>
                  }
                />
                <Route
                  path="skills"
                  element={
                    <ModuleSuspense moduleName="技能">
                      <SkillsPanel />
                    </ModuleSuspense>
                  }
                />
                <Route
                  path="workflow"
                  element={
                    <ModuleSuspense moduleName="工作流">
                      <WorkflowPanel />
                    </ModuleSuspense>
                  }
                />
                <Route
                  path="subagent"
                  element={
                    <ModuleSuspense moduleName="子代理">
                      <SubagentPanel />
                    </ModuleSuspense>
                  }
                />
                <Route
                  path="tools"
                  element={
                    <ModuleSuspense moduleName="工具管理">
                      <ToolsPanel />
                    </ModuleSuspense>
                  }
                />
                <Route
                  path="pet"
                  element={
                    <ModuleSuspense moduleName="宠物">
                      <PetPanel />
                    </ModuleSuspense>
                  }
                />
                <Route
                  path="performance"
                  element={
                    <ModuleSuspense moduleName="性能监控">
                      <PerformancePanel />
                    </ModuleSuspense>
                  }
                />
                <Route
                  path="notification"
                  element={
                    <ModuleSuspense moduleName="通知">
                      <NotificationPanel />
                    </ModuleSuspense>
                  }
                />
                <Route
                  path="settings"
                  element={
                    <ModuleSuspense moduleName="设置">
                      <SettingsPanel />
                    </ModuleSuspense>
                  }
                />
              </Route>
            </Routes>

            {/* 命令面板 — 全局覆盖层 */}
            <CommandPalette open={commandPaletteOpen} onClose={closeCommandPalette} />
          </BrowserRouter>
        </ThemeProvider>
      </QueryClientProvider>
    </GlobalErrorBoundary>
  )
}
