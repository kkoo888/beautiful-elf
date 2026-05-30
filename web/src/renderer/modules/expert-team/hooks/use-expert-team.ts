/** 专家团工作流状态管理 hook */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useCallback, useState } from 'react'
import type {
  ExpertTeam,
  ExpertTeamFormInput,
  ExpertTeamUpdateInput,
  ExpertMemberFormInput,
  ExpertTeamRun,
  ExpertTeamExecuteInput,
  ExpertTeamExecuteResult,
} from '../types'
import {
  fetchExpertTeams,
  fetchExpertTeamById,
  createExpertTeam,
  updateExpertTeam,
  deleteExpertTeam,
  addExpertMember,
  updateExpertMember,
  deleteExpertMember,
  executeExpertTeam,
  fetchExpertTeamRuns,
  fetchAllExpertRuns,
} from '../services/expert-team-api'

const TEAM_KEY = ['expert-teams']
const RUN_KEY = ['expert-team-runs']

export interface UseExpertTeamReturn {
  // 列表
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

  // CRUD 操作
  createTeamMut: (input: ExpertTeamFormInput) => Promise<ExpertTeam>
  updateTeamMut: (id: number, input: ExpertTeamUpdateInput) => Promise<ExpertTeam>
  deleteTeamMut: (id: number) => Promise<void>

  // 成员操作
  addMemberMut: (teamId: number, input: ExpertMemberFormInput) => Promise<unknown>
  updateMemberMut: (memberId: number, input: Partial<ExpertMemberFormInput>) => Promise<unknown>
  deleteMemberMut: (memberId: number) => Promise<void>

  // 执行
  executeTeamMut: (teamId: number, input: ExpertTeamExecuteInput) => Promise<ExpertTeamExecuteResult>
  isExecuting: boolean

  // 状态
  isMutating: boolean

  // 刷新
  refreshTeams: () => void
  refreshRuns: () => void
}

export function useExpertTeam(): UseExpertTeamReturn {
  const queryClient = useQueryClient()
  const [selectedId, setSelectedId] = useState<number | null>(null)
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

  const refreshRuns = useCallback(() => {
    void queryClient.invalidateQueries({ queryKey: RUN_KEY })
  }, [queryClient])

  // CRUD mutations — onSuccess 自动刷新，无需手动调用
  const createMut = useMutation({
    mutationFn: (input: ExpertTeamFormInput) => createExpertTeam(input),
    onSuccess: refreshTeams,
  })

  const updateMut = useMutation({
    mutationFn: ({ id, input }: { id: number; input: ExpertTeamUpdateInput }) =>
      updateExpertTeam(id, input),
    onSuccess: refreshTeams,
  })

  const deleteMut = useMutation({
    mutationFn: (id: number) => deleteExpertTeam(id),
    onSuccess: () => {
      refreshTeams()
      setSelectedId(null)
    },
  })

  // 成员 mutations
  const addMemberMut = useMutation({
    mutationFn: ({ teamId, input }: { teamId: number; input: ExpertMemberFormInput }) =>
      addExpertMember(teamId, input),
    onSuccess: refreshTeams,
  })

  const updateMemberMut = useMutation({
    mutationFn: ({ memberId, input }: { memberId: number; input: Partial<ExpertMemberFormInput> }) =>
      updateExpertMember(memberId, input),
    onSuccess: refreshTeams,
  })

  const deleteMemberMut = useMutation({
    mutationFn: (memberId: number) => deleteExpertMember(memberId),
    onSuccess: refreshTeams,
  })

  // 执行 mutation
  const executeMut = useMutation({
    mutationFn: ({ teamId, input }: { teamId: number; input: ExpertTeamExecuteInput }) =>
      executeExpertTeam(teamId, input),
    onSuccess: refreshRuns,
  })

  // 包装函数 — 参数展平
  const createTeamMut = useCallback(
    (input: ExpertTeamFormInput) => createMut.mutateAsync(input),
    [createMut]
  )

  const updateTeamMut = useCallback(
    (id: number, input: ExpertTeamUpdateInput) => updateMut.mutateAsync({ id, input }),
    [updateMut]
  )

  const deleteTeamMut = useCallback(
    (id: number) => deleteMut.mutateAsync(id),
    [deleteMut]
  )

  const addMemberMutFn = useCallback(
    (teamId: number, input: ExpertMemberFormInput) =>
      addMemberMut.mutateAsync({ teamId, input }),
    [addMemberMut]
  )

  const updateMemberMutFn = useCallback(
    (memberId: number, input: Partial<ExpertMemberFormInput>) =>
      updateMemberMut.mutateAsync({ memberId, input }),
    [updateMemberMut]
  )

  const deleteMemberMutFn = useCallback(
    (memberId: number) => deleteMemberMut.mutateAsync(memberId),
    [deleteMemberMut]
  )

  const executeTeamMut = useCallback(
    (teamId: number, input: ExpertTeamExecuteInput) =>
      executeMut.mutateAsync({ teamId, input }),
    [executeMut]
  )

  const isMutating =
    createMut.isPending ||
    updateMut.isPending ||
    deleteMut.isPending ||
    addMemberMut.isPending ||
    updateMemberMut.isPending ||
    deleteMemberMut.isPending

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
    createTeamMut,
    updateTeamMut,
    deleteTeamMut,
    addMemberMut: addMemberMutFn,
    updateMemberMut: updateMemberMutFn,
    deleteMemberMut: deleteMemberMutFn,
    executeTeamMut,
    isExecuting: executeMut.isPending,
    isMutating,
    refreshTeams,
    refreshRuns,
  }
}
