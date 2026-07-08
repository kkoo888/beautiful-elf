import React from 'react'
import { ModuleErrorBoundary } from '@/components/error-boundary/module-error-boundary'
import { LoadingSkeleton } from '@/components/loading/loading-skeleton'

/**
 * 页面级 Suspense 包裹器
 * 每个页面独立加载状态 + 错误边界
 */
function PageSuspense({
  children,
  moduleName,
}: {
  children: React.ReactNode
  moduleName: string
}) {
  return (
    <ModuleErrorBoundary moduleName={moduleName}>
      <React.Suspense fallback={<LoadingSkeleton type="text" rows={4} />}>
        {children}
      </React.Suspense>
    </ModuleErrorBoundary>
  )
}

// 懒加载所有页面
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
const ExpertTeamPanel = React.lazy(() => import('@/modules/expert-team'))
const ImageGalleryPanel = React.lazy(() => import('@/modules/image-gallery'))
const VideoGalleryPanel = React.lazy(() => import('@/modules/video-gallery'))
const IntentLearningPanel = React.lazy(() => import('@/modules/intent-learning/intent-learning-panel'))

export function ChatPage() {
  return (
    <PageSuspense moduleName="对话">
      <ChatPanel />
    </PageSuspense>
  )
}

export function SchedulePage() {
  return (
    <PageSuspense moduleName="日程">
      <SchedulePanel />
    </PageSuspense>
  )
}

export function ClipboardPage() {
  return (
    <PageSuspense moduleName="剪贴板">
      <ClipboardPanel />
    </PageSuspense>
  )
}

export function SnippetsPage() {
  return (
    <PageSuspense moduleName="代码片段">
      <SnippetsPanel />
    </PageSuspense>
  )
}

export function KnowledgePage() {
  return (
    <PageSuspense moduleName="知识库">
      <KnowledgePanel />
    </PageSuspense>
  )
}

export function MemoryPage() {
  return (
    <PageSuspense moduleName="记忆">
      <MemoryPanel />
    </PageSuspense>
  )
}

export function TranslatePage() {
  return (
    <PageSuspense moduleName="翻译">
      <TranslatePanel />
    </PageSuspense>
  )
}

export function SkillsPage() {
  return (
    <PageSuspense moduleName="技能">
      <SkillsPanel />
    </PageSuspense>
  )
}

export function WorkflowPage() {
  return (
    <PageSuspense moduleName="工作流">
      <WorkflowPanel />
    </PageSuspense>
  )
}

export function SubagentPage() {
  return (
    <PageSuspense moduleName="子代理">
      <SubagentPanel />
    </PageSuspense>
  )
}

export function ToolsPage() {
  return (
    <PageSuspense moduleName="工具管理">
      <ToolsPanel />
    </PageSuspense>
  )
}

export function PetPage() {
  return (
    <PageSuspense moduleName="宠物">
      <PetPanel />
    </PageSuspense>
  )
}

export function PerformancePage() {
  return (
    <PageSuspense moduleName="性能监控">
      <PerformancePanel />
    </PageSuspense>
  )
}

export function NotificationPage() {
  return (
    <PageSuspense moduleName="通知">
      <NotificationPanel />
    </PageSuspense>
  )
}

export function SettingsPage() {
  return (
    <PageSuspense moduleName="设置">
      <SettingsPanel />
    </PageSuspense>
  )
}

export function ExpertTeamPage() {
  return (
    <PageSuspense moduleName="专家团">
      <ExpertTeamPanel />
    </PageSuspense>
  )
}

export function ImageGalleryPage() {
  return (
    <PageSuspense moduleName="图片画廊">
      <ImageGalleryPanel />
    </PageSuspense>
  )
}

export function VideoGalleryPage() {
  return (
    <PageSuspense moduleName="视频画廊">
      <VideoGalleryPanel />
    </PageSuspense>
  )
}

export function IntentLearningPage() {
  return (
    <PageSuspense moduleName="意图学习">
      <IntentLearningPanel />
    </PageSuspense>
  )
}
