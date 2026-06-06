/** 工作流状态管理 hook（TanStack Query + React Flow） */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useCallback, useState, useEffect, useMemo } from 'react'
import type {
  Workflow,
  WorkflowRun,
  WorkflowTemplate,
  WorkflowFormInput,
  WorkflowNode,
  WorkflowEdge,
} from '../types/workflow'
import {
  fetchWorkflows,
  fetchWorkflowRuns,
  fetchWorkflowTemplates,
  createWorkflow,
  updateWorkflow,
  deleteWorkflow,
  createFromTemplate,
  saveWorkflowDag,
  runWorkflow,
  stopWorkflow,
  duplicateWorkflow,
} from '../services/workflow-api'
import { pollingRegistry } from '@/services/polling-registry'
import { useAppStore } from '@/stores/use-app-store'

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
  /** 保存 DAG */
  saveDagMut: (nodes: WorkflowNode[], edges: WorkflowEdge[]) => Promise<void>
  /** 运行工作流 */
  runWorkflowMut: (id: string) => Promise<void>
  /** 停止工作流 */
  stopWorkflowMut: (id: string) => Promise<void>
  /** 复制工作流 */
  duplicateWorkflowMut: (id: string) => Promise<void>
  /** 是否有正在提交的操作 */
  isMutating: boolean
  /** 选中的工作流 */
  selectedWorkflow: Workflow | undefined
  /** 当前编辑器节点 */
  nodes: WorkflowNode[]
  setNodes: (nodes: WorkflowNode[]) => void
  /** 当前编辑器边 */
  edges: WorkflowEdge[]
  setEdges: (edges: WorkflowEdge[]) => void
}

export function useWorkflow(): UseWorkflowReturn {
  const queryClient = useQueryClient()
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'list' | 'editor' | 'templates' | 'monitor'>('list')

  // React Flow 编辑器状态
  const [nodes, setNodes] = useState<WorkflowNode[]>([])
  const [edges, setEdges] = useState<WorkflowEdge[]>([])

  const {
    data: workflows = [],
    isLoading,
    error,
  } = useQuery({
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

  const selectedWorkflow = useMemo(
    () => workflows.find((w) => w.id === selectedId),
    [workflows, selectedId]
  )

  // 选中工作流变更时，同步编辑器节点/边
  useEffect(() => {
    if (selectedWorkflow) {
      setNodes(selectedWorkflow.nodes)
      setEdges(selectedWorkflow.edges)
    } else {
      setNodes([])
      setEdges([])
    }
  }, [selectedId, selectedWorkflow])

  const invalidateAll = useCallback(() => {
    void queryClient.invalidateQueries({ queryKey: WORKFLOW_KEY })
    void queryClient.invalidateQueries({ queryKey: RUN_KEY })
  }, [queryClient])

  const createMut = useMutation({
    mutationFn: (input: WorkflowFormInput) => createWorkflow(input),
    onSuccess: invalidateAll,
  })

  const updateMut = useMutation({
    mutationFn: ({ id, input }: { id: string; input: Partial<WorkflowFormInput> }) =>
      updateWorkflow(id, input),
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

  const saveDagMutInner = useMutation({
    mutationFn: ({
      workflowId,
      nodes: n,
      edges: e,
    }: {
      workflowId: string
      nodes: WorkflowNode[]
      edges: WorkflowEdge[]
    }) => saveWorkflowDag(workflowId, n, e),
    onSuccess: invalidateAll,
  })

  const runMut = useMutation({
    mutationFn: (id: string) => runWorkflow(id),
    onSuccess: invalidateAll,
  })

  const stopMut = useMutation({
    mutationFn: (id: string) => stopWorkflow(id),
    onSuccess: invalidateAll,
  })

  const duplicateMut = useMutation({
    mutationFn: (id: string) => duplicateWorkflow(id),
    onSuccess: invalidateAll,
  })

  const createWorkflowMut = useCallback(
    (input: WorkflowFormInput) => createMut.mutateAsync(input),
    [createMut]
  )
  const updateWorkflowMut = useCallback(
    (id: string, input: Partial<WorkflowFormInput>) => updateMut.mutateAsync({ id, input }),
    [updateMut]
  )
  const deleteWorkflowMut = useCallback((id: string) => deleteMut.mutateAsync(id), [deleteMut])
  const createFromTemplateMut = useCallback(
    (templateId: string) => templateMut.mutateAsync(templateId),
    [templateMut]
  )

  const saveDagMut = useCallback(
    (n: WorkflowNode[], e: WorkflowEdge[]) => {
      if (!selectedId) return Promise.resolve()
      return saveDagMutInner.mutateAsync({ workflowId: selectedId, nodes: n, edges: e })
    },
    [selectedId, saveDagMutInner]
  )

  const runWorkflowMut = useCallback((id: string) => runMut.mutateAsync(id), [runMut])
  const stopWorkflowMut = useCallback((id: string) => stopMut.mutateAsync(id), [stopMut])
  const duplicateWorkflowMut = useCallback(
    (id: string) => duplicateMut.mutateAsync(id),
    [duplicateMut]
  )

  const isMutating =
    createMut.isPending ||
    updateMut.isPending ||
    deleteMut.isPending ||
    templateMut.isPending ||
    saveDagMutInner.isPending ||
    runMut.isPending ||
    stopMut.isPending ||
    duplicateMut.isPending

  // 轮询：定期刷新工作流和运行记录
  const pollingEnabled = useAppStore((s) => s.pollingEnabled)
  useEffect(() => {
    const POLLING_ID = 'workflow:status'
    if (pollingEnabled) {
      pollingRegistry.register({
        id: POLLING_ID,
        module: 'workflow',
        interval: 15_000,
        callback: async () => {
          await Promise.all([
            queryClient.invalidateQueries({ queryKey: WORKFLOW_KEY }),
            queryClient.invalidateQueries({ queryKey: RUN_KEY }),
          ])
        },
        enabled: true,
      })
    }
    return () => {
      pollingRegistry.unregister(POLLING_ID)
    }
  }, [pollingEnabled, queryClient])

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
    saveDagMut,
    runWorkflowMut,
    stopWorkflowMut,
    duplicateWorkflowMut,
    isMutating,
    selectedWorkflow,
    nodes,
    setNodes,
    edges,
    setEdges,
  }
}
