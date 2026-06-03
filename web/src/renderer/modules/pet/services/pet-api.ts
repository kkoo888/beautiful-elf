/**
 * 宠物 API 服务
 *
 * 后端 Query 参数: page, page_size → snake_case
 * 后端 CamelModel 请求体: populate_by_name=True
 */

import { apiClient, extractData } from '@/services/api-client'
import type { PetAttributes } from '@/types'
import type { PetInteraction, PetInteractionType } from '../types/pet'

const INTERACTION_TYPE_MAP: Record<PetInteractionType, number> = { feed: 0, clean: 1, chat: 2, play: 3 }
const INTERACTION_TYPE_NAME_MAP: Record<number, PetInteractionType> = { 0: 'feed', 1: 'clean', 2: 'chat', 3: 'play' }
const INTERACT_EFFECTS: Record<PetInteractionType, string> = { feed: '饥饿度 +20', clean: '清洁度 +20', chat: '心情 +15, 亲密 +5', play: '心情 +25, 经验 +10' }

export async function fetchPetAttributes(): Promise<PetAttributes> {
  const data = extractData(await apiClient.get('/pets')) as Record<string, number>
  return { hunger: data.hunger, clean: data.clean, mood: data.mood, health: data.health, intimacy: data.intimacy, level: data.level }
}

export async function interact(type: PetInteractionType): Promise<{ attributes: PetAttributes; interaction: PetInteraction }> {
  const result = extractData(await apiClient.post('/pets/interactions', { interaction_type: INTERACTION_TYPE_MAP[type] })) as any
  return {
    attributes: { hunger: result.pet.hunger, clean: result.pet.clean, mood: result.pet.mood, health: result.pet.health, intimacy: result.pet.intimacy, level: result.pet.level },
    interaction: { id: String(Date.now()), type, effect: INTERACT_EFFECTS[type], createdAt: new Date().toISOString() },
  }
}

export async function fetchInteractions(params: { page?: number; pageSize?: number } = {}): Promise<PetInteraction[]> {
  const items = extractData(await apiClient.get('/pets/interactions', {
    params: { page: params.page ?? 1, pageSize: params.pageSize ?? 20 },
  })) as any[]
  return items.map((item) => ({
    id: String(item.id), type: INTERACTION_TYPE_NAME_MAP[item.interactionType] ?? 'feed',
    effect: item.effectDesc ?? '', createdAt: item.createdAt ?? new Date().toISOString(),
  }))
}

export async function scanModels(dirPath: string): Promise<{ name: string; path: string; size: number }[]> {
  const data = extractData(await apiClient.post('/pets/models/scan', { dir_path: dirPath })) as any
  return data?.models ?? []
}

export async function switchPetModel(modelPath: string): Promise<void> {
  await apiClient.post('/pets/models/switch', { model_path: modelPath })
}

export async function loadPetSettings(): Promise<Record<string, unknown> | null> {
  try {
    const item = extractData(await apiClient.get('/configs/pet_settings')) as Record<string, unknown>
    if (item?.keyValue) return JSON.parse(item.keyValue as string)
  } catch { /* key 不存在 */ }
  return null
}

export async function savePetSettings(settings: Record<string, unknown>): Promise<void> {
  const jsonStr = JSON.stringify(settings)
  try { await apiClient.put('/configs/pet_settings', { keyValue: jsonStr, description: '宠物设置（JSON）' }) }
  catch { await apiClient.post('/configs', { settingsKey: 'pet_settings', keyValue: jsonStr, description: '宠物设置（JSON）' }) }
}

export async function loadPetModelPath(): Promise<string | null> {
  try {
    const item = extractData(await apiClient.get('/configs/pet_model_path')) as Record<string, unknown>
    return (item?.keyValue as string) ?? null
  } catch { return null }
}
