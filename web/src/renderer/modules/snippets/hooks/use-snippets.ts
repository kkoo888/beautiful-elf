import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useMessage } from '@/hooks/use-message'
import {
  fetchSnippets,
  createSnippet,
  updateSnippet,
  deleteSnippet,
  recordSnippetUse,
  fetchAllTags,
} from '../services/snippets-api'
import type { SnippetFormData, SnippetQueryParams } from '../types/snippets'

/** 查询 key */
const QUERY_KEYS = {
  snippets: ['snippets'] as const,
  snippetList: (params?: SnippetQueryParams) => ['snippets', 'list', params] as const,
  tags: ['snippets', 'tags'] as const,
}

/** 获取片段列表 */
export function useSnippets(params?: SnippetQueryParams) {
  return useQuery({
    queryKey: QUERY_KEYS.snippetList(params),
    queryFn: () => fetchSnippets(params),
  })
}

/** 获取所有标签 */
export function useSnippetTags() {
  return useQuery({
    queryKey: QUERY_KEYS.tags,
    queryFn: fetchAllTags,
  })
}

/** 创建片段 */
export function useCreateSnippet() {
  const queryClient = useQueryClient()
  const { message } = useMessage()

  return useMutation({
    mutationFn: (data: SnippetFormData) => createSnippet(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: QUERY_KEYS.snippets })
      message.success('片段创建成功')
    },
    onError: () => {
      message.error('创建失败，请重试')
    },
  })
}

/** 更新片段 */
export function useUpdateSnippet() {
  const queryClient = useQueryClient()
  const { message } = useMessage()

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: SnippetFormData }) => updateSnippet(id, data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: QUERY_KEYS.snippets })
      message.success('片段更新成功')
    },
    onError: () => {
      message.error('更新失败，请重试')
    },
  })
}

/** 删除片段 */
export function useDeleteSnippet() {
  const queryClient = useQueryClient()
  const { message } = useMessage()

  return useMutation({
    mutationFn: (id: string) => deleteSnippet(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: QUERY_KEYS.snippets })
      message.success('片段已删除')
    },
    onError: () => {
      message.error('删除失败，请重试')
    },
  })
}

/** 记录片段使用 */
export function useRecordSnippetUse() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => recordSnippetUse(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: QUERY_KEYS.snippets })
    },
  })
}
