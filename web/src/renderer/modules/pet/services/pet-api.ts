/**
 * 宠物 API 服务
 *
 * 后端 Query 参数: page, page_size → snake_case
 * 后端 CamelModel 请求体: populate_by_name=True
 */

import { apiClient, extractData } from '@/services/api-client'
import type { PetAttributes } from '@/types'
import type { PetInteraction, PetInteractionType } from '../types/pet'
import {
  PET_INTERACTION_TYPE_ID,
  PET_INTERACTION_ID_TYPE,
  PET_INTERACTION_EFFECT_DESC,
} from '../types/pet'

export async function fetchPetAttributes(): Promise<PetAttributes> {
  const data = extractData(await apiClient.get('/pets')) as Record<string, number>
  return { hunger: data.hunger, clean: data.clean, mood: data.mood, health: data.health, intimacy: data.intimacy, level: data.level }
}

export async function interact(type: PetInteractionType): Promise<{ attributes: PetAttributes; interaction: PetInteraction }> {
  const result = extractData(await apiClient.post('/pets/interactions', { interaction_type: PET_INTERACTION_TYPE_ID[type] })) as any
  return {
    attributes: { hunger: result.pet.hunger, clean: result.pet.clean, mood: result.pet.mood, health: result.pet.health, intimacy: result.pet.intimacy, level: result.pet.level },
    interaction: { id: String(Date.now()), type, effect: PET_INTERACTION_EFFECT_DESC[type], createdAt: new Date().toISOString() },
  }
}

export async function fetchInteractions(params: { page?: number; pageSize?: number } = {}): Promise<PetInteraction[]> {
  const items = extractData(await apiClient.get('/pets/interactions', {
    params: { page: params.page ?? 1, pageSize: params.pageSize ?? 20 },
  })) as any[]
  return items.map((item) => ({
    id: String(item.id), type: PET_INTERACTION_ID_TYPE[item.interactionType] ?? 'feed',
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
