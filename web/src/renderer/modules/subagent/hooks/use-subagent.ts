/** 子代理状态管理 hook（TanStack Query） */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useCallback, useState, useMemo } from 'react'
import type { SubagentRun } from '../types/subagent'
import { fetchSubagentRuns, stopSubagentRun, stopAllSubagentRuns } from '../services/subagent-api'

const QUERY_KEY = ['subagent-runs']

export interface UseSubagentReturn {
  /** 运行列表 */
  runs: SubagentRun[]
  /** 加载中 */
  isLoading: boolean
  /** 错误 */
  error: Error | null
  /** 运行中的数量 */
  runningCount: number
  /** 选中的运行 ID */
  selectedId: string | null
  setSelectedId: (id: string | null) => void
  /** 选中的运行 */
  selectedRun: SubagentRun | undefined
  /** 终止单个 */
  stopRunMut: (id: string) => Promise<SubagentRun>
  /** 终止全部 */
  stopAllMut: () => Promise<number>
  /** 是否有正在提交的操作 */
  isMutating: boolean
}

export function useSubagent(): UseSubagentReturn {
  const queryClient = useQueryClient()
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const { data: runs = [], isLoading, error } = useQuery({
    queryKey: QUERY_KEY,
    queryFn: fetchSubagentRuns,
    refetchInterval: 5000, // 每 5 秒刷新
  })

  const runningCount = useMemo(() => runs.filter((r) => r.status === 'running').length, [runs])

  const invalidate = useCallback(() => {
    void queryClient.invalidateQueries({ queryKey: QUERY_KEY })
  }, [queryClient])

  const stopMut = useMutation({
    mutationFn: (id: string) => stopSubagentRun(id),
    onSuccess: invalidate,
  })

  const stopAllMut = useMutation({
    mutationFn: () => stopAllSubagentRuns(),
    onSuccess: invalidate,
  })

  const stopRunMut = useCallback((id: string) => stopMut.mutateAsync(id), [stopMut])
  const stopAll = useCallback(() => stopAllMut.mutateAsync(), [stopAllMut])

  const isMutating = stopMut.isPending || stopAllMut.isPending

  const selectedRun = runs.find((r) => r.id === selectedId)

  return {
    runs,
    isLoading,
    error: error as Error | null,
    runningCount,
    selectedId,
    setSelectedId,
    selectedRun,
    stopRunMut,
    stopAllMut: stopAll,
    isMutating,
  }
}
