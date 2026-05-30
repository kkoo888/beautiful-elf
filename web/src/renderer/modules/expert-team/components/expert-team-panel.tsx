/** 专家团工作流主面板 */

import { Tabs, Button, Space, Typography, Spin, message } from 'antd'
import {
  PlusOutlined,
  TeamOutlined,
  PlayCircleOutlined,
  HistoryOutlined,
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

/** 专家团工作流主面板 */
export default function ExpertTeamPanel() {
  const {
    teams,
    isLoading,
    selectedId,
    setSelectedId,
    selectedTeam,
    activeTab,
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

  // 执行抽屉
  const [executeDrawerOpen, setExecuteDrawerOpen] = useState(false)
  const [executeTeam, setExecuteTeam] = useState<ExpertTeam | null>(null)

  // 新建
  const handleCreate = useCallback(async () => {
    setActiveTab('editor')
    setSelectedId(null)
  }, [setActiveTab, setSelectedId])

  // 编辑
  const handleEdit = useCallback(
    (id: number) => {
      setSelectedId(id)
      setActiveTab('editor')
    },
    [setSelectedId, setActiveTab]
  )

  // 查看详情
  const handleViewDetail = useCallback(
    (id: number) => {
      setSelectedId(id)
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

  // 保存（新建/编辑）— mutation onSuccess 自动刷新列表
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
      setActiveTab('list')
    },
    [selectedId, createTeamMut, updateTeamMut, setSelectedId, setActiveTab]
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
      setActiveTab('monitor')
      refreshRuns()
    },
    [executeTeam, executeTeamMut, setActiveTab, refreshRuns]
  )

  // Tab items
  const tabItems = [
    {
      key: 'list',
      label: (
        <Space>
          <TeamOutlined />
          专家团列表
        </Space>
      ),
      children: (
        <ExpertTeamList
          teams={teams}
          loading={isLoading}
          onView={handleViewDetail}
          onEdit={handleEdit}
          onDelete={handleDelete}
          onExecute={handleExecute}
        />
      ),
    },
    {
      key: 'editor',
      label: (
        <Space>
          <PlusOutlined />
          {selectedId ? '编辑专家团' : '新建专家团'}
        </Space>
      ),
      children: (
        <ExpertTeamEditor
          team={selectedTeam}
          onSave={handleSave}
          onCancel={() => setActiveTab('list')}
          loading={isMutating}
        />
      ),
    },
    {
      key: 'detail',
      label: (
        <Space>
          <TeamOutlined />
          专家团详情
        </Space>
      ),
      children: selectedTeam ? (
        <ExpertTeamDetail
          team={selectedTeam}
          onEdit={() => handleEdit(selectedTeam.id)}
          onExecute={() => handleExecute(selectedTeam)}
        />
      ) : null,
    },
    {
      key: 'monitor',
      label: (
        <Space>
          <HistoryOutlined />
          运行记录
          {runsTotal > 0 && <Text type="secondary">({runsTotal})</Text>}
        </Space>
      ),
      children: (
        <ExpertTeamMonitor
          runs={runs}
          loading={isRunsLoading}
          onRefresh={refreshRuns}
        />
      ),
    },
  ]

  return (
    <ModuleErrorBoundary module="expert-team">
      <div style={{ padding: '0 24px 24px' }}>
        <PageHeader
          title="👥 专家团工作流"
          subtitle="多专家协作，AI 驱动的智能分析"
          extra={
            <Space>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={handleCreate}
              >
                新建专家团
              </Button>
              <Button
                icon={<PlayCircleOutlined />}
                onClick={() => setActiveTab('monitor')}
              >
                运行记录
              </Button>
            </Space>
          }
        />

        <Tabs
          activeKey={activeTab}
          onChange={(key) => setActiveTab(key as typeof activeTab)}
          items={tabItems}
          style={{ marginTop: 16 }}
        />

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
