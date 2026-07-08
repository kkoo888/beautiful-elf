import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  fetchCorrections,
  fetchPatterns,
  fetchSuggestions,
  acceptSuggestion,
  ignoreSuggestion,
  analyzeBehavior,
  createIntentFromPattern,
} from '../services/intent-api'

export function useIntentCorrections() {
  return useQuery({
    queryKey: ['intent-corrections'],
    queryFn: fetchCorrections,
  })
}

export function useBehaviorPatterns() {
  return useQuery({
    queryKey: ['behavior-patterns'],
    queryFn: fetchPatterns,
  })
}

export function useSkillSuggestions() {
  const queryClient = useQueryClient()

  const query = useQuery({
    queryKey: ['skill-suggestions'],
    queryFn: fetchSuggestions,
  })

  const accept = useMutation({
    mutationFn: acceptSuggestion,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['skill-suggestions'] })
      queryClient.invalidateQueries({ queryKey: ['skills'] })  // 刷新技能列表
    },
  })

  const ignore = useMutation({
    mutationFn: ignoreSuggestion,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['skill-suggestions'] })
    },
  })

  return {
    ...query,
    acceptSuggestion: accept.mutateAsync,
    ignoreSuggestion: ignore.mutateAsync,
  }
}

export function useAnalyzeBehavior() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: analyzeBehavior,
    onSuccess: () => {
      // 分析完成后刷新所有相关数据
      queryClient.invalidateQueries({ queryKey: ['behavior-patterns'] })
      queryClient.invalidateQueries({ queryKey: ['skill-suggestions'] })
    },
  })
}

export function useCreateIntentFromPattern() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: createIntentFromPattern,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['behavior-patterns'] })
    },
  })
}
