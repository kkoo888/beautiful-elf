/** 工具管理状态管理 hook（TanStack Query） */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { message } from 'antd'
import type { ToolInfo, ToolQueryParams, CreateToolInput, UpdateToolInput } from '../types/tools'
import {
  fetchTools, createTool, updateTool, deleteTool,
  enableTool, disableTool,
} from '../services/tools-api'

const TOOLS_KEY = ['tools']

export interface UseToolsReturn {
  /** 工具列表 */
  tools: ToolInfo[]
  /** 加载中 */
  isLoading: boolean
  /** 错误 */
  error: Error | null
  /** 总条数 */
  total: number
  /** 合并数据（目前直接透传 tools） */
  toolsWithStats: ToolInfo[]
  /** 统计汇总（从列表数据 + total 计算） */
  summary: import('../types/tools').ToolStatsSummary
  /** 汇总加载中 */
  isSummaryLoading: boolean
  /** 手动刷新 */
  refetch: () => void
}

export function useTools(params?: ToolQueryParams): UseToolsReturn {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: [...TOOLS_KEY, params?.page, params?.pageSize, params?.isEnabled],
    queryFn: () => fetchTools(params),
  })

  const tools = data?.items ?? []
  const total = data?.total ?? 0

  // 直接从分页数据计算汇总，无需额外请求
  const summary = {
    totalTools: total,
    activeTools: tools.filter((t) => t.isEnabled === 1).length,
    totalCalls: 0,
    avgSuccessRate: 0,
  }

  return {
    tools,
    isLoading,
    error: error as Error | null,
    total,
    toolsWithStats: tools,
    summary,
    isSummaryLoading: isLoading,
    refetch: () => void refetch(),
  }
}

/** 新增工具 */
export function useCreateTool() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (input: CreateToolInput) => createTool(input),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: TOOLS_KEY })
      message.success('工具创建成功')
    },
    onError: (e: Error) => message.error(`创建失败: ${e.message}`),
  })
}

/** 编辑工具 */
export function useUpdateTool() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, input }: { id: number; input: UpdateToolInput }) => updateTool(id, input),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: TOOLS_KEY })
      message.success('工具更新成功')
    },
    onError: (e: Error) => message.error(`更新失败: ${e.message}`),
  })
}

/** 删除工具 */
export function useDeleteTool() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => deleteTool(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: TOOLS_KEY })
      message.success('工具已删除')
    },
    onError: (e: Error) => message.error(`删除失败: ${e.message}`),
  })
}

/** 启用/禁用工具 */
export function useToggleTool() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, enable }: { id: number; enable: boolean }) =>
      enable ? enableTool(id) : disableTool(id),
    onSuccess: (_: unknown, vars: { id: number; enable: boolean }) => {
      qc.invalidateQueries({ queryKey: TOOLS_KEY })
      message.success(vars.enable ? '工具已启用' : '工具已禁用')
    },
    onError: (e: Error) => message.error(`操作失败: ${e.message}`),
  })
}
