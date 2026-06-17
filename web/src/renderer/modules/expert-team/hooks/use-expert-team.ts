/** 专家团工作流状态管理 hook */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useCallback, useState } from 'react'
import type {
  ExpertTeam,
  ExpertTeamFormInput,
  ExpertTeamUpdateInput,
  ExpertTeamBindExperts,
  Expert,
  ExpertFormInput,
  ExpertSkillCreate,
  ExpertSkillUpdate,
  ExpertTeamRun,
  ExpertTeamExecuteInput,
  ExpertTeamExecuteResult,
} from '../types'
import {
  fetchExperts,
  createExpert,
  updateExpert,
  deleteExpert,
  fetchExpertSkills,
  bindExpertSkill,
  updateExpertSkillBind,
  unbindExpertSkill,
  fetchExpertTeams,
  fetchExpertTeamById,
  createExpertTeam,
  updateExpertTeam,
  deleteExpertTeam,
  bindExpertsToTeam,
  executeExpertTeam,
  fetchExpertTeamRuns,
  fetchAllExpertRuns,
} from '../services/expert-team-api'

const TEAM_KEY = ['expert-teams']
const EXPERT_KEY = ['experts']
const RUN_KEY = ['expert-team-runs']

export interface UseExpertTeamReturn {
  // 专家团列表
  teams: ExpertTeam[]
  isLoading: boolean
  error: Error | null
  total: number

  // 选中
  selectedId: number | null
  setSelectedId: (id: number | null) => void
  selectedTeam: ExpertTeam | undefined

  // Tab
  activeTab: 'list' | 'detail' | 'editor' | 'monitor'
  setActiveTab: (tab: 'list' | 'detail' | 'editor' | 'monitor') => void

  // 运行记录
  runs: ExpertTeamRun[]
  isRunsLoading: boolean
  runsTotal: number

  // 专家列表
  experts: Expert[]
  isExpertsLoading: boolean
  expertsTotal: number

  // 专家团 CRUD
  createTeamMut: (input: ExpertTeamFormInput) => Promise<ExpertTeam>
  updateTeamMut: (id: number, input: ExpertTeamUpdateInput) => Promise<ExpertTeam>
  deleteTeamMut: (id: number) => Promise<void>
  bindExpertsMut: (teamId: number, data: ExpertTeamBindExperts) => Promise<ExpertTeam>

  // 专家 CRUD
  createExpertMut: (input: ExpertFormInput) => Promise<Expert>
  updateExpertMut: (id: number, input: Partial<ExpertFormInput>) => Promise<Expert>
  deleteExpertMut: (id: number) => Promise<void>

  // 专家技能
  expertSkills: any[]
  isSkillsLoading: boolean
  bindSkillMut: (expertId: number, input: ExpertSkillCreate) => Promise<unknown>
  updateSkillBindMut: (bindId: number, input: ExpertSkillUpdate) => Promise<unknown>
  unbindSkillMut: (bindId: number) => Promise<void>
  selectedExpertId: number | null
  setSelectedExpertId: (id: number | null) => void

  // 执行
  executeTeamMut: (teamId: number, input: ExpertTeamExecuteInput) => Promise<ExpertTeamExecuteResult>
  isExecuting: boolean

  // 状态
  isMutating: boolean

  // 刷新
  refreshTeams: () => void
  refreshExperts: () => void
  refreshRuns: () => void
  refreshSkills: () => void
}

export function useExpertTeam(): UseExpertTeamReturn {
  const queryClient = useQueryClient()
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [selectedExpertId, setSelectedExpertId] = useState<number | null>(null)
  const [activeTab, setActiveTab] = useState<'list' | 'detail' | 'editor' | 'monitor'>('list')

  // 专家团列表
  const {
    data: teamsData,
    isLoading,
    error,
  } = useQuery({
    queryKey: TEAM_KEY,
    queryFn: () => fetchExpertTeams(),
  })

  const teams = teamsData?.items ?? []
  const total = teamsData?.total ?? 0

  // 选中的专家团
  const selectedTeam = teams.find((t) => t.id === selectedId)

  // 独立专家列表
  const {
    data: expertsData,
    isLoading: isExpertsLoading,
  } = useQuery({
    queryKey: EXPERT_KEY,
    queryFn: () => fetchExperts(),
  })

  const experts = expertsData?.items ?? []
  const expertsTotal = expertsData?.total ?? 0

  // 专家技能
  const {
    data: expertSkills = [],
    isLoading: isSkillsLoading,
  } = useQuery({
    queryKey: ['expert-skills', selectedExpertId],
    queryFn: () => fetchExpertSkills(selectedExpertId!),
    enabled: !!selectedExpertId,
  })

  // 运行记录
  const { data: runsData, isLoading: isRunsLoading } = useQuery({
    queryKey: RUN_KEY,
    queryFn: () => fetchAllExpertRuns(),
    enabled: activeTab === 'monitor',
  })

  const runs = runsData?.items ?? []
  const runsTotal = runsData?.total ?? 0

  // 刷新
  const refreshTeams = useCallback(() => {
    void queryClient.invalidateQueries({ queryKey: TEAM_KEY })
  }, [queryClient])

  const refreshExperts = useCallback(() => {
    void queryClient.invalidateQueries({ queryKey: EXPERT_KEY })
  }, [queryClient])

  const refreshRuns = useCallback(() => {
    void queryClient.invalidateQueries({ queryKey: RUN_KEY })
  }, [queryClient])

  const refreshSkills = useCallback(() => {
    void queryClient.invalidateQueries({ queryKey: ['expert-skills', selectedExpertId] })
  }, [queryClient, selectedExpertId])

  // 专家团 CRUD mutations
  const createTeamMutation = useMutation({
    mutationFn: (input: ExpertTeamFormInput) => createExpertTeam(input),
    onSuccess: refreshTeams,
  })

  const updateTeamMutation = useMutation({
    mutationFn: ({ id, input }: { id: number; input: ExpertTeamUpdateInput }) =>
      updateExpertTeam(id, input),
    onSuccess: refreshTeams,
  })

  const deleteTeamMutation = useMutation({
    mutationFn: (id: number) => deleteExpertTeam(id),
    onSuccess: () => {
      refreshTeams()
      setSelectedId(null)
    },
  })

  const bindExpertsMutation = useMutation({
    mutationFn: ({ teamId, data }: { teamId: number; data: ExpertTeamBindExperts }) =>
      bindExpertsToTeam(teamId, data),
    onSuccess: () => {
      refreshTeams()
    },
  })

  // 专家 CRUD mutations
  const createExpertMutation = useMutation({
    mutationFn: (input: ExpertFormInput) => createExpert(input),
    onSuccess: () => {
      refreshExperts()
      refreshTeams()
    },
  })

  const updateExpertMutation = useMutation({
    mutationFn: ({ id, input }: { id: number; input: Partial<ExpertFormInput> }) =>
      updateExpert(id, input),
    onSuccess: () => {
      refreshExperts()
      refreshTeams()
    },
  })

  const deleteExpertMutation = useMutation({
    mutationFn: (id: number) => deleteExpert(id),
    onSuccess: () => {
      refreshExperts()
      refreshTeams()
    },
  })

  // 专家技能 mutations
  const bindSkillMutation = useMutation({
    mutationFn: ({ expertId, input }: { expertId: number; input: ExpertSkillCreate }) =>
      bindExpertSkill(expertId, input),
    onSuccess: refreshSkills,
  })

  const updateSkillBindMutation = useMutation({
    mutationFn: ({ bindId, input }: { bindId: number; input: ExpertSkillUpdate }) =>
      updateExpertSkillBind(bindId, input),
    onSuccess: refreshSkills,
  })

  const unbindSkillMutation = useMutation({
    mutationFn: (bindId: number) => unbindExpertSkill(bindId),
    onSuccess: refreshSkills,
  })

  // 执行 mutation
  const executeMut = useMutation({
    mutationFn: ({ teamId, input }: { teamId: number; input: ExpertTeamExecuteInput }) =>
      executeExpertTeam(teamId, input),
    onSuccess: refreshRuns,
  })

  // 包装函数 — 参数展平
  const createTeamMut = useCallback(
    (input: ExpertTeamFormInput) => createTeamMutation.mutateAsync(input),
    [createTeamMutation]
  )

  const updateTeamMut = useCallback(
    (id: number, input: ExpertTeamUpdateInput) => updateTeamMutation.mutateAsync({ id, input }),
    [updateTeamMutation]
  )

  const deleteTeamMut = useCallback(
    (id: number) => deleteTeamMutation.mutateAsync(id),
    [deleteTeamMutation]
  )

  const bindExpertsMutFn = useCallback(
    (teamId: number, data: ExpertTeamBindExperts) =>
      bindExpertsMutation.mutateAsync({ teamId, data }),
    [bindExpertsMutation]
  )

  const createExpertMutFn = useCallback(
    (input: ExpertFormInput) => createExpertMutation.mutateAsync(input),
    [createExpertMutation]
  )

  const updateExpertMutFn = useCallback(
    (id: number, input: Partial<ExpertFormInput>) =>
      updateExpertMutation.mutateAsync({ id, input }),
    [updateExpertMutation]
  )

  const deleteExpertMutFn = useCallback(
    (id: number) => deleteExpertMutation.mutateAsync(id),
    [deleteExpertMutation]
  )

  const bindSkillMutFn = useCallback(
    (expertId: number, input: ExpertSkillCreate) =>
      bindSkillMutation.mutateAsync({ expertId, input }),
    [bindSkillMutation]
  )

  const updateSkillBindMutFn = useCallback(
    (bindId: number, input: ExpertSkillUpdate) =>
      updateSkillBindMutation.mutateAsync({ bindId, input }),
    [updateSkillBindMutation]
  )

  const unbindSkillMutFn = useCallback(
    (bindId: number) => unbindSkillMutation.mutateAsync(bindId),
    [unbindSkillMutation]
  )

  const executeTeamMut = useCallback(
    (teamId: number, input: ExpertTeamExecuteInput) =>
      executeMut.mutateAsync({ teamId, input }),
    [executeMut]
  )

  const isMutating =
    createTeamMutation.isPending ||
    updateTeamMutation.isPending ||
    deleteTeamMutation.isPending ||
    bindExpertsMutation.isPending ||
    createExpertMutation.isPending ||
    updateExpertMutation.isPending ||
    deleteExpertMutation.isPending

  return {
    teams,
    isLoading,
    error: error as Error | null,
    total,
    selectedId,
    setSelectedId,
    selectedTeam,
    activeTab,
    setActiveTab,
    runs,
    isRunsLoading,
    runsTotal,
    experts,
    isExpertsLoading,
    expertsTotal,
    createTeamMut,
    updateTeamMut,
    deleteTeamMut,
    bindExpertsMut: bindExpertsMutFn,
    createExpertMut: createExpertMutFn,
    updateExpertMut: updateExpertMutFn,
    deleteExpertMut: deleteExpertMutFn,
    expertSkills,
    isSkillsLoading,
    bindSkillMut: bindSkillMutFn,
    updateSkillBindMut: updateSkillBindMutFn,
    unbindSkillMut: unbindSkillMutFn,
    selectedExpertId,
    setSelectedExpertId,
    executeTeamMut,
    isExecuting: executeMut.isPending,
    isMutating,
    refreshTeams,
    refreshExperts,
    refreshRuns,
    refreshSkills,
  }
}
