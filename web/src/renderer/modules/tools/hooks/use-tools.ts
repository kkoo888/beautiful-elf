/** 工具管理状态管理 hook（TanStack Query） */

import { useQuery } from '@tanstack/react-query'
import { useMemo } from 'react'
import type { ToolInfo, ToolStats, ToolStatsSummary } from '../types/tools'
import { fetchTools, fetchToolStats, fetchToolStatsSummary } from '../services/tools-api'

const TOOLS_KEY = ['tools']
const STATS_KEY = ['tool-stats']
const SUMMARY_KEY = ['tool-stats-summary']

export interface UseToolsReturn {
  /** 工具列表 */
  tools: ToolInfo[]
  /** 工具加载中 */
  isLoading: boolean
  /** 错误 */
  error: Error | null
  /** 调用统计 */
  stats: ToolStats[]
  /** 统计加载中 */
  isStatsLoading: boolean
  /** 统计汇总 */
  summary: ToolStatsSummary | undefined
  /** 汇总加载中 */
  isSummaryLoading: boolean
  /** 合并数据（工具信息 + 统计） */
  toolsWithStats: Array<ToolInfo & Partial<ToolStats>>
}

export function useTools(): UseToolsReturn {
  const {
    data: tools = [],
    isLoading,
    error,
  } = useQuery({
    queryKey: TOOLS_KEY,
    queryFn: fetchTools,
  })

  const { data: stats = [], isLoading: isStatsLoading } = useQuery({
    queryKey: STATS_KEY,
    queryFn: fetchToolStats,
  })

  const { data: summary, isLoading: isSummaryLoading } = useQuery({
    queryKey: SUMMARY_KEY,
    queryFn: fetchToolStatsSummary,
  })

  const toolsWithStats = useMemo(() => {
    const statsMap = new Map(stats.map((s) => [s.toolId, s]))
    return tools.map((tool) => ({ ...tool, ...statsMap.get(tool.id) }))
  }, [tools, stats])

  return {
    tools,
    isLoading,
    error: error as Error | null,
    stats,
    isStatsLoading,
    summary,
    isSummaryLoading,
    toolsWithStats,
  }
}
