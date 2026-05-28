/** 工作流状态管理 hook（TanStack Query） */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useCallback, useState } from 'react'
import type { Workflow, WorkflowRun, WorkflowTemplate, WorkflowFormInput } from '../types/workflow'
import {
  fetchWorkflows,
  fetchWorkflowRuns,
  fetchWorkflowTemplates,
  createWorkflow,
  updateWorkflow,
  deleteWorkflow,
  createFromTemplate,
  reorderSteps,
} from '../services/workflow-api'

const WORKFLOW_KEY = ['workflows']
const RUN_KEY = ['workflow-runs']
const TEMPLATE_KEY = ['workflow-templates']

export interface UseWorkflowReturn {
  /** 工作流列表 */
  workflows: Workflow[]
  /** 加载中 */
  isLoading: boolean
  /** 错误 */
  error: Error | null
  /** 运行记录 */
  runs: WorkflowRun[]
  /** 运行记录加载中 */
  isRunsLoading: boolean
  /** 模板列表 */
  templates: WorkflowTemplate[]
  /** 模板加载中 */
  isTemplatesLoading: boolean
  /** 当前选中的工作流 ID */
  selectedId: string | null
  setSelectedId: (id: string | null) => void
  /** 当前 tab */
  activeTab: 'list' | 'editor' | 'templates' | 'monitor'
  setActiveTab: (tab: 'list' | 'editor' | 'templates' | 'monitor') => void
  /** 创建工作流 */
  createWorkflowMut: (input: WorkflowFormInput) => Promise<Workflow>
  /** 更新工作流 */
  updateWorkflowMut: (id: string, input: Partial<WorkflowFormInput>) => Promise<Workflow>
  /** 删除工作流 */
  deleteWorkflowMut: (id: string) => Promise<void>
  /** 从模板创建 */
  createFromTemplateMut: (templateId: string) => Promise<Workflow>
  /** 重排步骤 */
  reorderStepsMut: (workflowId: string, stepIds: string[]) => Promise<Workflow>
  /** 是否有正在提交的操作 */
  isMutating: boolean
  /** 选中的工作流 */
  selectedWorkflow: Workflow | undefined
}

export function useWorkflow(): UseWorkflowReturn {
  const queryClient = useQueryClient()
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'list' | 'editor' | 'templates' | 'monitor'>('list')

  const { data: workflows = [], isLoading, error } = useQuery({
    queryKey: WORKFLOW_KEY,
    queryFn: fetchWorkflows,
  })

  const { data: runs = [], isLoading: isRunsLoading } = useQuery({
    queryKey: RUN_KEY,
    queryFn: () => fetchWorkflowRuns(),
  })

  const { data: templates = [], isLoading: isTemplatesLoading } = useQuery({
    queryKey: TEMPLATE_KEY,
    queryFn: fetchWorkflowTemplates,
  })

  const invalidateAll = useCallback(() => {
    void queryClient.invalidateQueries({ queryKey: WORKFLOW_KEY })
    void queryClient.invalidateQueries({ queryKey: RUN_KEY })
  }, [queryClient])

  const createMut = useMutation({
    mutationFn: (input: WorkflowFormInput) => createWorkflow(input),
    onSuccess: invalidateAll,
  })

  const updateMut = useMutation({
    mutationFn: ({ id, input }: { id: string; input: Partial<WorkflowFormInput> }) => updateWorkflow(id, input),
    onSuccess: invalidateAll,
  })

  const deleteMut = useMutation({
    mutationFn: (id: string) => deleteWorkflow(id),
    onSuccess: invalidateAll,
  })

  const templateMut = useMutation({
    mutationFn: (templateId: string) => createFromTemplate(templateId),
    onSuccess: invalidateAll,
  })

  const reorderMut = useMutation({
    mutationFn: ({ workflowId, stepIds }: { workflowId: string; stepIds: string[] }) => reorderSteps(workflowId, stepIds),
    onSuccess: invalidateAll,
  })

  const createWorkflowMut = useCallback((input: WorkflowFormInput) => createMut.mutateAsync(input), [createMut])
  const updateWorkflowMut = useCallback((id: string, input: Partial<WorkflowFormInput>) => updateMut.mutateAsync({ id, input }), [updateMut])
  const deleteWorkflowMut = useCallback((id: string) => deleteMut.mutateAsync(id), [deleteMut])
  const createFromTemplateMut = useCallback((templateId: string) => templateMut.mutateAsync(templateId), [templateMut])
  const reorderStepsMut = useCallback((workflowId: string, stepIds: string[]) => reorderMut.mutateAsync({ workflowId, stepIds }), [reorderMut])

  const isMutating = createMut.isPending || updateMut.isPending || deleteMut.isPending || templateMut.isPending || reorderMut.isPending

  const selectedWorkflow = workflows.find((w) => w.id === selectedId)

  return {
    workflows,
    isLoading,
    error: error as Error | null,
    runs,
    isRunsLoading,
    templates,
    isTemplatesLoading,
    selectedId,
    setSelectedId,
    activeTab,
    setActiveTab,
    createWorkflowMut,
    updateWorkflowMut,
    deleteWorkflowMut,
    createFromTemplateMut,
    reorderStepsMut,
    isMutating,
    selectedWorkflow,
  }
}
