import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchPetAttributes, interact, fetchInteractions } from '../services/pet-api'
import type { PetInteractionType } from '../types/pet'

export function usePet() {
  const queryClient = useQueryClient()

  const { data: attributes, isLoading } = useQuery({
    queryKey: ['pet-attributes'],
    queryFn: fetchPetAttributes,
    refetchInterval: 30000,
  })

  const { data: interactions = [] } = useQuery({
    queryKey: ['pet-interactions'],
    queryFn: fetchInteractions,
  })

  const mutation = useMutation({
    mutationFn: (type: PetInteractionType) => interact(type),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pet-attributes'] })
      queryClient.invalidateQueries({ queryKey: ['pet-interactions'] })
    },
  })

  return {
    attributes: attributes ?? { hunger: 0, clean: 0, mood: 0, health: 0, intimacy: 0, level: 0 },
    isLoading,
    interact: mutation.mutateAsync,
    interactions,
  }
}
