/** 专家团工作流状态管理 hook */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useCallback, useState, useRef } from 'react'
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
  type ExpertTeamSSEEvent,
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
  executeTeamMut: (teamId: number, input: ExpertTeamExecuteInput) => Promise<void>
  isExecuting: boolean
  // SSE 实时事件
  liveEvents: ExpertTeamSSEEvent[]
  liveExperts: Map<string, { name: string; role: string; avatar: string; status: string; thinking: string; durationMs: number }>
  liveStatus: string
  liveOutput: string
  resetLive: () => void

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

  // SSE 实时状态
  const [liveEvents, setLiveEvents] = useState<ExpertTeamSSEEvent[]>([])
  const [liveExperts, setLiveExperts] = useState<Map<string, { name: string; role: string; avatar: string; status: string; thinking: string; durationMs: number }>>(new Map())
  const [liveStatus, setLiveStatus] = useState<string>('idle')
  const [liveOutput, setLiveOutput] = useState<string>('')
  const abortRef = useRef<AbortController | null>(null)

  const resetLive = useCallback(() => {
    setLiveEvents([])
    setLiveExperts(new Map())
    setLiveStatus('idle')
    setLiveOutput('')
  }, [])

  // 执行 mutation
  const [isExecuting, setIsExecuting] = useState(false)

  const executeTeamMut = useCallback(
    async (teamId: number, input: ExpertTeamExecuteInput) => {
      setIsExecuting(true)
      resetLive()
      setLiveStatus('running')
      abortRef.current = new AbortController()

      try {
        await executeExpertTeam(teamId, input, (event) => {
          setLiveEvents((prev) => [...prev, event])

          if (event.type === 'expert_start') {
            const key = `${event.expertName}-${event.expertRole}`
            setLiveExperts((prev) => {
              const next = new Map(prev)
              next.set(key, {
                name: event.expertName || '',
                role: event.expertRole || '',
                avatar: event.avatar || '🤖',
                status: 'running',
                thinking: '',
                durationMs: 0,
              })
              return next
            })
            setLiveStatus('discussing')
          } else if (event.type === 'expert_done') {
            const key = `${event.expertName}-${event.expertRole}`
            setLiveExperts((prev) => {
              const next = new Map(prev)
              const existing = next.get(key)
              next.set(key, {
                name: event.expertName || '',
                role: event.expertRole || '',
                avatar: event.avatar || '🤖',
                status: 'done',
                thinking: existing?.thinking || '',
                durationMs: event.durationMs || 0,
              })
              return next
            })
          } else if (event.type === 'expert_thinking') {
            const key = `${event.expertName}-${event.expertRole}`
            setLiveExperts((prev) => {
              const next = new Map(prev)
              const existing = next.get(key)
              next.set(key, {
                name: event.expertName || '',
                role: event.expertRole || '',
                avatar: event.avatar || '🤖',
                status: existing?.status || 'running',
                thinking: event.content || '',
                durationMs: event.durationMs || existing?.durationMs || 0,
              })
              return next
            })
          } else if (event.type === 'pm_done') {
            setLiveStatus('orchestrating')
            // PM 开始分析
            const pmKey = `${event.expertName || 'PM'}-PM/组长`
            setLiveExperts((prev) => {
              const next = new Map(prev)
              next.set(pmKey, {
                name: event.expertName || 'PM',
                role: 'PM/组长',
                avatar: '🎯',
                status: 'running',
                thinking: event.content || '',
                durationMs: 0,
              })
              return next
            })
          } else if (event.type === 'pm_eval') {
            setLiveStatus('synthesizing')
            const pmKey = `${event.expertName || 'PM'}-PM/组长`
            setLiveExperts((prev) => {
              const next = new Map(prev)
              const existing = next.get(pmKey)
              next.set(pmKey, {
                name: event.expertName || 'PM',
                role: 'PM/组长',
                avatar: '🎯',
                status: 'done',
                thinking: event.content || existing?.thinking || '',
                durationMs: existing?.durationMs || 0,
              })
              return next
            })
          } else if (event.type === 'pm_report') {
            setLiveOutput(event.content || '')
            setLiveStatus('completed')
          } else if (event.type === 'done') {
            setLiveStatus('completed')
            refreshRuns()
          } else if (event.type === 'error') {
            setLiveStatus('failed')
          }
        }, abortRef.current.signal)
      } catch (err) {
        if ((err as Error).name !== 'AbortError') {
          setLiveStatus('failed')
          throw err
        }
      } finally {
        setIsExecuting(false)
      }
    },
    [refreshRuns, resetLive],
  )

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
    isExecuting,
    isMutating,
    refreshTeams,
    refreshExperts,
    refreshRuns,
    refreshSkills,
    // SSE 实时状态
    liveEvents,
    liveExperts,
    liveStatus,
    liveOutput,
    resetLive,
  }
}
