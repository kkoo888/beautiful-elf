import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  fetchScenes, fetchScene, createScene, updateScene, deleteScene, activateScene,
  fetchSceneBlocks, placeBlock, removeBlock,
  fetchBlocks, createBlock, deleteBlock,
} from '../services/virtual-world-api'
import type { VirtualWorldSceneFormData, VirtualWorldBlockFormData } from '../types'

// ── Scene hooks ──

export function useScenes(page = 1, pageSize = 20) {
  return useQuery({
    queryKey: ['virtual-world-scenes', page, pageSize],
    queryFn: () => fetchScenes({ page, pageSize }),
  })
}

export function useScene(id: number | null) {
  return useQuery({
    queryKey: ['virtual-world-scene', id],
    queryFn: () => fetchScene(id!),
    enabled: id !== null,
  })
}

export function useCreateScene() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: VirtualWorldSceneFormData) => createScene(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['virtual-world-scenes'] }),
  })
}

export function useUpdateScene() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<VirtualWorldSceneFormData> }) => updateScene(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['virtual-world-scenes'] }),
  })
}

export function useDeleteScene() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => deleteScene(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['virtual-world-scenes'] }),
  })
}

export function useActivateScene() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => activateScene(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['virtual-world-scenes'] }),
  })
}

// ── Scene Block hooks ──

export function useSceneBlocks(sceneId: number | null) {
  return useQuery({
    queryKey: ['virtual-world-scene-blocks', sceneId],
    queryFn: () => fetchSceneBlocks(sceneId!),
    enabled: sceneId !== null,
  })
}

export function usePlaceBlock(sceneId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: { blockId: string; posX: number; posY: number; posZ: number; rotationY?: number; material?: string }) =>
      placeBlock(sceneId, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['virtual-world-scene-blocks', sceneId] }),
  })
}

export function useRemoveBlock(sceneId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ x, y, z }: { x: number; y: number; z: number }) => removeBlock(sceneId, x, y, z),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['virtual-world-scene-blocks', sceneId] }),
  })
}

// ── Block Type hooks ──

export function useBlocks(page = 1, pageSize = 100) {
  return useQuery({
    queryKey: ['virtual-world-blocks', page, pageSize],
    queryFn: () => fetchBlocks({ page, pageSize }),
  })
}

export function useCreateBlock() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: VirtualWorldBlockFormData) => createBlock(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['virtual-world-blocks'] }),
  })
}

export function useDeleteBlock() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => deleteBlock(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['virtual-world-blocks'] }),
  })
}
