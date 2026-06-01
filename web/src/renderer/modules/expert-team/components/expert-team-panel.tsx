/** 专家团工作流主面板 */

import { Button, Space, Typography, message, Breadcrumb } from 'antd'
import {
  PlusOutlined,
  TeamOutlined,
  PlayCircleOutlined,
  HistoryOutlined,
  ArrowLeftOutlined,
} from '@ant-design/icons'
import { useState, useCallback } from 'react'
import { PageHeader } from '@/components/page-header'
import { ModuleErrorBoundary } from '@/components/error-boundary/module-error-boundary'
import { useExpertTeam } from '../hooks/use-expert-team'
import { ExpertTeamList } from './expert-team-list'
import { ExpertTeamDetail } from './expert-team-detail'
import { ExpertTeamEditor } from './expert-team-editor'
import { ExpertTeamMonitor } from './expert-team-monitor'
import { ExpertTeamExecuteDrawer } from './expert-team-execute-drawer'
import type { ExpertTeam, ExpertTeamFormInput, ExpertTeamExecuteInput } from '../types'

const { Text } = Typography

type ViewMode = 'list' | 'detail' | 'editor' | 'monitor'

/** 专家团工作流主面板 */
export default function ExpertTeamPanel() {
  const {
    teams,
    isLoading,
    selectedId,
    setSelectedId,
    selectedTeam,
    setActiveTab,
    runs,
    isRunsLoading,
    runsTotal,
    createTeamMut,
    updateTeamMut,
    deleteTeamMut,
    executeTeamMut,
    isExecuting,
    isMutating,
    refreshRuns,
  } = useExpertTeam()

  const [view, setView] = useState<ViewMode>('list')

  // 执行抽屉
  const [executeDrawerOpen, setExecuteDrawerOpen] = useState(false)
  const [executeTeam, setExecuteTeam] = useState<ExpertTeam | null>(null)

  // 导航到列表
  const goList = useCallback(() => {
    setView('list')
    setSelectedId(null)
    setActiveTab('list')
  }, [setSelectedId, setActiveTab])

  // 新建
  const handleCreate = useCallback(() => {
    setSelectedId(null)
    setView('editor')
    setActiveTab('editor')
  }, [setSelectedId, setActiveTab])

  // 编辑
  const handleEdit = useCallback(
    (id: number) => {
      setSelectedId(id)
      setView('editor')
      setActiveTab('editor')
    },
    [setSelectedId, setActiveTab]
  )

  // 查看详情
  const handleViewDetail = useCallback(
    (id: number) => {
      setSelectedId(id)
      setView('detail')
      setActiveTab('detail')
    },
    [setSelectedId, setActiveTab]
  )

  // 删除
  const handleDelete = useCallback(
    async (id: number) => {
      await deleteTeamMut(id)
      message.success('已删除')
    },
    [deleteTeamMut]
  )

  // 保存（新建/编辑）
  const handleSave = useCallback(
    async (input: ExpertTeamFormInput) => {
      if (selectedId) {
        await updateTeamMut(selectedId, input)
        message.success('已更新')
      } else {
        const team = await createTeamMut(input)
        setSelectedId(team.id)
        message.success('已创建')
      }
      goList()
    },
    [selectedId, createTeamMut, updateTeamMut, setSelectedId, goList]
  )

  // 执行
  const handleExecute = useCallback(
    (team: ExpertTeam) => {
      setExecuteTeam(team)
      setExecuteDrawerOpen(true)
    },
    []
  )

  const handleExecuteSubmit = useCallback(
    async (input: ExpertTeamExecuteInput) => {
      if (!executeTeam) return
      const result = await executeTeamMut(executeTeam.id, input)
      message.success(`执行完成！共 ${result.rounds} 轮讨论，耗时 ${(result.durationMs / 1000).toFixed(1)}s`)
      setExecuteDrawerOpen(false)
      setView('monitor')
      setActiveTab('monitor')
      refreshRuns()
    },
    [executeTeam, executeTeamMut, setActiveTab, refreshRuns]
  )

  // 渲染页面标题和返回按钮
  const renderHeader = () => {
    if (view === 'list') {
      return (
        <PageHeader
          title="👥 专家团工作流"
          subtitle="多专家协作，AI 驱动的智能分析"
          extra={
            <Space>
              <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
                新建专家团
              </Button>
              <Button icon={<HistoryOutlined />} onClick={() => { setView('monitor'); setActiveTab('monitor') }}>
                运行记录
              </Button>
            </Space>
          }
        />
      )
    }

    const titles: Record<ViewMode, string> = {
      list: '',
      detail: '专家团详情',
      editor: selectedId ? '编辑专家团' : '新建专家团',
      monitor: '运行记录',
    }

    return (
      <div style={{ marginBottom: 16 }}>
        <Breadcrumb
          items={[
            { title: <a onClick={goList}>专家团列表</a> },
            { title: titles[view] },
          ]}
          style={{ marginBottom: 12 }}
        />
        <Space align="center">
          <Button icon={<ArrowLeftOutlined />} onClick={goList}>
            返回列表
          </Button>
          <Text strong style={{ fontSize: 16 }}>{titles[view]}</Text>
        </Space>
      </div>
    )
  }

  // 渲染当前视图
  const renderView = () => {
    switch (view) {
      case 'list':
        return (
          <ExpertTeamList
            teams={teams}
            loading={isLoading}
            onView={handleViewDetail}
            onEdit={handleEdit}
            onDelete={handleDelete}
            onExecute={handleExecute}
          />
        )

      case 'detail':
        return selectedTeam ? (
          <ExpertTeamDetail
            team={selectedTeam}
            onEdit={() => handleEdit(selectedTeam.id)}
            onExecute={() => handleExecute(selectedTeam)}
          />
        ) : null

      case 'editor':
        return (
          <ExpertTeamEditor
            key={selectedId ?? 'new'}
            team={selectedTeam}
            onSave={handleSave}
            onCancel={goList}
            loading={isMutating}
          />
        )

      case 'monitor':
        return (
          <ExpertTeamMonitor
            runs={runs}
            loading={isRunsLoading}
            onRefresh={refreshRuns}
          />
        )

      default:
        return null
    }
  }

  return (
    <ModuleErrorBoundary module="expert-team">
      <div style={{ padding: '0 24px 24px' }}>
        {renderHeader()}
        {renderView()}

        {/* 执行抽屉 */}
        <ExpertTeamExecuteDrawer
          open={executeDrawerOpen}
          team={executeTeam}
          onClose={() => setExecuteDrawerOpen(false)}
          onSubmit={handleExecuteSubmit}
          loading={isExecuting}
        />
      </div>
    </ModuleErrorBoundary>
  )
}
