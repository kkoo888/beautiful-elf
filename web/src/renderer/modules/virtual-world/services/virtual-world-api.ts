import { apiClient, extractData, extractPaginated } from '@/services/api-client'
import type {
  VirtualWorldScene,
  VirtualWorldBlock,
  VirtualWorldSceneBlock,
  VirtualWorldSceneFormData,
  VirtualWorldBlockFormData,
} from '../types'

// ── Scene ──

export async function fetchScenes(params?: { page?: number; pageSize?: number }) {
  const { items, total } = extractPaginated(
    (await apiClient.get('/virtualworld/scenes', {
      params: { page: params?.page ?? 1, pageSize: params?.pageSize ?? 20 },
    })) as unknown as { items: unknown[]; total: number },
  )
  return { items: items as VirtualWorldScene[], total }
}

export async function fetchScene(id: number): Promise<VirtualWorldScene> {
  return extractData(await apiClient.get(`/virtualworld/scenes/${id}`)) as VirtualWorldScene
}

export async function createScene(data: VirtualWorldSceneFormData): Promise<VirtualWorldScene> {
  return extractData(await apiClient.post('/virtualworld/scenes', data)) as VirtualWorldScene
}

export async function updateScene(id: number, data: Partial<VirtualWorldSceneFormData>): Promise<VirtualWorldScene> {
  return extractData(await apiClient.put(`/virtualworld/scenes/${id}`, data)) as VirtualWorldScene
}

export async function deleteScene(id: number): Promise<void> {
  await apiClient.delete(`/virtualworld/scenes/${id}`)
}

export async function activateScene(id: number): Promise<VirtualWorldScene> {
  return extractData(await apiClient.post(`/virtualworld/scenes/${id}/activate`)) as VirtualWorldScene
}

// ── Scene Blocks ──

export async function fetchSceneBlocks(sceneId: number): Promise<VirtualWorldSceneBlock[]> {
  return extractData(await apiClient.get(`/virtualworld/scenes/${sceneId}/blocks`)) as VirtualWorldSceneBlock[]
}

export async function placeBlock(sceneId: number, data: {
  blockId: string
  posX: number
  posY: number
  posZ: number
  rotationY?: number
  material?: string
}): Promise<VirtualWorldSceneBlock> {
  return extractData(await apiClient.post(`/virtualworld/scenes/${sceneId}/blocks`, data)) as VirtualWorldSceneBlock
}

export async function removeBlock(sceneId: number, x: number, y: number, z: number): Promise<void> {
  await apiClient.delete(`/virtualworld/scenes/${sceneId}/blocks/${x}/${y}/${z}`)
}

// ── Block Types ──

export async function fetchBlocks(params?: { page?: number; pageSize?: number }) {
  const { items, total } = extractPaginated(
    (await apiClient.get('/virtualworld/blocks', {
      params: { page: params?.page ?? 1, pageSize: params?.pageSize ?? 100 },
    })) as unknown as { items: unknown[]; total: number },
  )
  return { items: items as VirtualWorldBlock[], total }
}

export async function createBlock(data: VirtualWorldBlockFormData): Promise<VirtualWorldBlock> {
  return extractData(await apiClient.post('/virtualworld/blocks', data)) as VirtualWorldBlock
}

export async function deleteBlock(id: number): Promise<void> {
  await apiClient.delete(`/virtualworld/blocks/${id}`)
}
