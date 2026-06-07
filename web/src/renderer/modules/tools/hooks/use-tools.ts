/** 工具管理状态管理 hook（TanStack Query） */

import { useQuery } from '@tanstack/react-query'
import type { ToolInfo } from '../types/tools'
import { fetchTools } from '../services/tools-api'

const TOOLS_KEY = ['tools']

export interface UseToolsReturn {
  /** 工具列表 */
  tools: ToolInfo[]
  /** 工具加载中 */
  isLoading: boolean
  /** 错误 */
  error: Error | null
  /** 合并数据（工具信息 + 统计，目前后端未提供汇总接口，直接透传 tools） */
  toolsWithStats: ToolInfo[]
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

  return {
    tools,
    isLoading,
    error: error as Error | null,
    toolsWithStats: tools,
  }
}
