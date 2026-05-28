/** 工作流主面板 */

import { Tabs, Button, Spin } from 'antd'
import { PlusOutlined, SyncOutlined } from '@ant-design/icons'
import { PageHeader } from '@/components/page-header'
import { useWorkflow } from '../hooks/use-workflow'
import { WorkflowList } from './workflow-list'
import { WorkflowEditor } from './workflow-editor'
import { WorkflowTemplates } from './workflow-templates'
import { WorkflowMonitor } from './workflow-monitor'
import type { WorkflowStep } from '../types/workflow'
import styles from './workflow-panel.module.css'

/** 工作流模块面板 */
export default function WorkflowPanel() {
  const {
    workflows,
    isLoading,
    runs,
    isRunsLoading,
    templates,
    isTemplatesLoading,
    selectedId,
    setSelectedId,
    activeTab,
    setActiveTab,
    createWorkflowMut,
    deleteWorkflowMut,
    createFromTemplateMut,
    reorderStepsMut,
    selectedWorkflow,
  } = useWorkflow()

  const handleEdit = (id: string) => {
    setSelectedId(id)
    setActiveTab('editor')
  }

  const handleStepsChange = (steps: WorkflowStep[]) => {
    if (selectedId) {
      void reorderStepsMut(selectedId, steps.map((s) => s.id))
    }
  }

  const tabItems = [
    {
      key: 'list',
      label: '工作流列表',
      children: (
        <WorkflowList
          workflows={workflows}
          loading={isLoading}
          onEdit={handleEdit}
          onDelete={(id) => void deleteWorkflowMut(id)}
          onRun={(id) => {
            // mock: 运行工作流
            void id
          }}
        />
      ),
    },
    {
      key: 'editor',
      label: '步骤编辑',
      children: selectedWorkflow ? (
        <WorkflowEditor
          steps={selectedWorkflow.steps}
          onStepsChange={handleStepsChange}
        />
      ) : (
        <div style={{ textAlign: 'center', padding: 48, color: 'var(--ant-color-text-secondary)' }}>
          请先在列表中选择一个工作流
        </div>
      ),
    },
    {
      key: 'templates',
      label: '模板库',
      children: (
        <WorkflowTemplates
          templates={templates}
          loading={isTemplatesLoading}
          onUseTemplate={(templateId) => void createFromTemplateMut(templateId)}
        />
      ),
    },
    {
      key: 'monitor',
      label: '运行监控',
      children: <WorkflowMonitor runs={runs} loading={isRunsLoading} />,
    },
  ]

  return (
    <div className={styles.panel}>
      <PageHeader
        title="⚙️ 工作流"
        description="工作流编排与运行监控"
        extra={
          <Button icon={<SyncOutlined />} onClick={() => void 0}>
            刷新
          </Button>
        }
      />
      <div className={styles.tabs}>
        <Tabs
          activeKey={activeTab}
          onChange={(key) => setActiveTab(key as typeof activeTab)}
          items={tabItems}
          className={styles.tabsContent}
        />
      </div>
    </div>
  )
}
