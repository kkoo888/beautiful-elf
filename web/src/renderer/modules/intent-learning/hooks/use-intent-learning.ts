import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  fetchCorrections,
  fetchPatterns,
  fetchSuggestions,
  acceptSuggestion,
  ignoreSuggestion,
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
