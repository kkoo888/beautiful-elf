/** 专家团工作流主面板 */

import { Button, Space, Typography, App, Breadcrumb } from 'antd'
import {
  PlusOutlined,
  PlayCircleOutlined,
  HistoryOutlined,
  ArrowLeftOutlined,
} from '@ant-design/icons'
import { useState, useCallback } from 'react'
import { ModuleErrorBoundary } from '@/components/error-boundary/module-error-boundary'
import { useExpertTeam } from '../hooks/use-expert-team'
import { ExpertTeamList } from './expert-team-list'
import { ExpertTeamDetail } from './expert-team-detail'
import { ExpertTeamEditor } from './expert-team-editor'
import { ExpertTeamMonitor } from './expert-team-monitor'
import { ExpertTeamExecuteDrawer } from './expert-team-execute-drawer'
import { ExpertTeamLivePanel } from './expert-team-live-panel'
import type { ExpertTeam, ExpertTeamFormInput, ExpertTeamExecuteInput } from '../types'
import styles from './expert-team.module.css'

const { Text } = Typography

type ViewMode = 'list' | 'detail' | 'editor' | 'monitor'

/** 专家团工作流主面板 */
export default function ExpertTeamPanel() {
  const { message } = App.useApp()
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
    refreshTeams,
    refreshRuns,
  } = useExpertTeam()

  const [view, setView] = useState<ViewMode>('list')

  // 执行抽屉
  const [executeDrawerOpen, setExecuteDrawerOpen] = useState(false)
  const [executeTeam, setExecuteTeam] = useState<ExpertTeam | null>(null)

  // 实时执行状态
  const [liveRunId, setLiveRunId] = useState<number | undefined>()
  const [liveMaxRounds, setLiveMaxRounds] = useState(3)

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
      setView('monitor')
      setActiveTab('monitor')
      setLiveRunId(undefined)
      setLiveMaxRounds(input.maxRounds || executeTeam.maxRounds)
      setExecuteDrawerOpen(false)

      const result = await executeTeamMut(executeTeam.id, input)
      setLiveRunId(result.runId)
      message.success(`执行完成！共 ${result.rounds} 轮讨论，耗时 ${(result.durationMs / 1000).toFixed(1)}s`)
      refreshRuns()
    },
    [executeTeam, executeTeamMut, setActiveTab, refreshRuns]
  )

  // 渲染页面标题和返回按钮
  const renderHeader = () => {
    if (view === 'list') {
      return (
        <div className={styles.toolbar}>
          <span className={styles.toolbarTitle}>
            {teams.length} 个专家团 · 多专家协作，AI 驱动的智能分析
          </span>
          <Space>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              新建专家团
            </Button>
            <Button icon={<HistoryOutlined />} onClick={() => { setView('monitor'); setActiveTab('monitor') }}>
              运行记录
            </Button>
          </Space>
        </div>
      )
    }

    const titles: Record<ViewMode, string> = {
      list: '',
      detail: '专家团详情',
      editor: selectedId ? '编辑专家团' : '新建专家团',
      monitor: '运行记录',
    }

    return (
      <div className={styles.subHeader}>
        <Breadcrumb
          items={[
            { title: <a onClick={goList}>专家团列表</a> },
            { title: titles[view] },
          ]}
        />
        <div className={styles.subHeaderRow}>
          <Button icon={<ArrowLeftOutlined />} onClick={goList}>
            返回列表
          </Button>
          <Text strong style={{ fontSize: 16 }}>{titles[view]}</Text>
        </div>
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
            onRefresh={refreshTeams}
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
          <div>
            <ExpertTeamLivePanel
              teamId={executeTeam?.id}
              runId={liveRunId}
              maxRounds={liveMaxRounds}
            />
            <div style={{ marginTop: 16 }}>
              <ExpertTeamMonitor
                runs={runs}
                loading={isRunsLoading}
                onRefresh={refreshRuns}
              />
            </div>
          </div>
        )

      default:
        return null
    }
  }

  return (
    <ModuleErrorBoundary module="expert-team">
      <div className={styles.panel}>
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
