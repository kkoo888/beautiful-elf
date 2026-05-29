import { apiClient } from '@/services/api-client'
import type { PetAttributes } from '@/types'
import type { PetInteraction, PetInteractionType } from '../types/pet'

// ── 类型映射 ──────────────────────────────────────────────────

/** 前端互动类型 → 后端 interaction_type 数字 */
const INTERACTION_TYPE_MAP: Record<PetInteractionType, number> = {
  feed: 0,
  clean: 1,
  chat: 2,
  play: 3,
}

/** 后端 interaction_type 数字 → 前端互动类型 */
const INTERACTION_TYPE_NAME_MAP: Record<number, PetInteractionType> = {
  0: 'feed',
  1: 'clean',
  2: 'chat',
  3: 'play',
}

/** 互动效果描述 */
const INTERACT_EFFECTS: Record<PetInteractionType, string> = {
  feed: '饥饿度 +20',
  clean: '清洁度 +20',
  chat: '心情 +15, 亲密 +5',
  play: '心情 +25, 经验 +10',
}

interface BackendPetAttributes {
  id: number
  hunger: number
  clean: number
  mood: number
  health: number
  intimacy: number
  level: number
  exp: number
  last_active_at: string | null
  created_at: string | null
  updated_at: string | null
}

interface BackendInteraction {
  id: number
  pet_attribute_id: number
  interaction_type: number
  interaction_type_name: string
  effect_desc: string
  effect_json: Record<string, number> | null
  created_at: string | null
}

function toFrontendPet(data: BackendPetAttributes): PetAttributes {
  return {
    hunger: data.hunger,
    clean: data.clean,
    mood: data.mood,
    health: data.health,
    intimacy: data.intimacy,
    level: data.level,
  }
}

// ── API 函数 ──────────────────────────────────────────────────

/** 获取宠物属性 */
export async function fetchPetAttributes(): Promise<PetAttributes> {
  const resp = await apiClient.get('/pets')
  return toFrontendPet((resp.data as any).data)
}

/** 宠物互动 */
export async function interact(
  type: PetInteractionType
): Promise<{ attributes: PetAttributes; interaction: PetInteraction }> {
  const resp = await apiClient.post('/pets/interactions', {
    interaction_type: INTERACTION_TYPE_MAP[type],
  })
  const result = (resp.data as any).data
  const interaction: PetInteraction = {
    id: String(Date.now()),
    type,
    effect: INTERACT_EFFECTS[type],
    createdAt: new Date().toISOString(),
  }
  return {
    attributes: toFrontendPet(result.pet),
    interaction,
  }
}

/** 获取互动记录 */
export async function fetchInteractions(
  params: { page?: number; pageSize?: number } = {}
): Promise<PetInteraction[]> {
  const resp = await apiClient.get('/pets/interactions', {
    params: { page: params.page ?? 1, page_size: params.pageSize ?? 20 },
  })
  const body = resp.data as any
  const items: BackendInteraction[] = body.data ?? []
  return items.map((item) => ({
    id: String(item.id),
    type: INTERACTION_TYPE_NAME_MAP[item.interaction_type] ?? 'feed',
    effect: item.effect_desc ?? '',
    createdAt: item.created_at ?? new Date().toISOString(),
  }))
}

// ─── 模型管理 ───

interface BackendModelInfo {
  name: string
  path: string
  size: number
}

interface BackendModelScanResponse {
  dir_path: string
  models: BackendModelInfo[]
}

/** 扫描指定目录下的 3D 模型文件 */
export async function scanModels(dirPath: string): Promise<BackendModelInfo[]> {
  const resp = await apiClient.post('/pets/models/scan', { dir_path: dirPath })
  const body = resp.data as any
  const data: BackendModelScanResponse = body.data
  return data.models
}

export async function switchPetModel(modelPath: string): Promise<void> {
  await apiClient.post('/pets/models/switch', { model_path: modelPath })
}

// ─── 宠物设置持久化 ───

interface BackendConfigItem {
  key_value: string
}

/** 加载宠物设置（从 configs 表读取 pet_settings） */
export async function loadPetSettings(): Promise<Record<string, unknown> | null> {
  try {
    const resp = await apiClient.get('/configs/pet_settings')
    const item = (resp.data as any).data as BackendConfigItem
    if (item?.key_value) {
      return JSON.parse(item.key_value)
    }
  } catch {
    // key 不存在返回 null
  }
  return null
}

/** 保存宠物设置（写入 configs 表 pet_settings） */
export async function savePetSettings(settings: Record<string, unknown>): Promise<void> {
  const jsonStr = JSON.stringify(settings)
  try {
    await apiClient.put('/configs/pet_settings', {
      value: jsonStr,
      description: '宠物设置（JSON）',
    })
  } catch {
    await apiClient.post('/configs', {
      key: 'pet_settings',
      value: jsonStr,
      description: '宠物设置（JSON）',
    })
  }
}

/** 获取已保存的模型路径（从 configs 表读取 pet_model_path） */
export async function loadPetModelPath(): Promise<string | null> {
  try {
    const resp = await apiClient.get('/configs/pet_model_path')
    const item = (resp.data as any).data as BackendConfigItem
    return item?.key_value ?? null
  } catch {
    return null
  }
}
