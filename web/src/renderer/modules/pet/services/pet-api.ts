import dayjs from 'dayjs'
import type { PetAttributes } from '@/types'
import type { PetInteraction, PetInteractionType } from '../types/pet'

const MOCK_ATTRIBUTES: PetAttributes = {
  hunger: 65,
  clean: 80,
  mood: 70,
  health: 90,
  intimacy: 35,
  level: 3,
}

const MOCK_INTERACTIONS: PetInteraction[] = [
  {
    id: '1',
    type: 'feed',
    effect: '饥饿度 +15',
    createdAt: dayjs().subtract(10, 'minute').toISOString(),
  },
  {
    id: '2',
    type: 'chat',
    effect: '心情 +10',
    createdAt: dayjs().subtract(30, 'minute').toISOString(),
  },
  {
    id: '3',
    type: 'clean',
    effect: '清洁度 +20',
    createdAt: dayjs().subtract(1, 'hour').toISOString(),
  },
  {
    id: '4',
    type: 'play',
    effect: '亲密 +5, 心情 +8',
    createdAt: dayjs().subtract(2, 'hour').toISOString(),
  },
  {
    id: '5',
    type: 'feed',
    effect: '饥饿度 +12',
    createdAt: dayjs().subtract(3, 'hour').toISOString(),
  },
  {
    id: '6',
    type: 'chat',
    effect: '心情 +6',
    createdAt: dayjs().subtract(5, 'hour').toISOString(),
  },
]

const INTERACT_EFFECTS: Record<
  PetInteractionType,
  { effect: string; delta: Partial<PetAttributes> }
> = {
  feed: { effect: '饥饿度 +15', delta: { hunger: 15 } },
  clean: { effect: '清洁度 +20', delta: { clean: 20 } },
  chat: { effect: '心情 +10, 亲密 +3', delta: { mood: 10, intimacy: 3 } },
  play: { effect: '心情 +8, 亲密 +5', delta: { mood: 8, intimacy: 5 } },
}

export async function fetchPetAttributes(): Promise<PetAttributes> {
  try {
    // const res = await apiClient.get<PetAttributes>('/pet/attributes')
    // return res.data
    throw new Error('use mock')
  } catch {
    return { ...MOCK_ATTRIBUTES }
  }
}

export async function interact(
  type: PetInteractionType
): Promise<{ attributes: PetAttributes; interaction: PetInteraction }> {
  try {
    // const res = await apiClient.post('/pet/interact', { type })
    // return res.data
    throw new Error('use mock')
  } catch {
    const meta = INTERACT_EFFECTS[type]
    const updated: PetAttributes = { ...MOCK_ATTRIBUTES }
    for (const [key, value] of Object.entries(meta.delta)) {
      const k = key as keyof PetAttributes
      const current = updated[k] as number
      ;(updated as Record<string, number>)[k] = Math.min(100, current + (value as number))
    }
    const interaction: PetInteraction = {
      id: Date.now().toString(),
      type,
      effect: meta.effect,
      createdAt: new Date().toISOString(),
    }
    return { attributes: updated, interaction }
  }
}

export async function fetchInteractions(): Promise<PetInteraction[]> {
  try {
    // const res = await apiClient.get<PetInteraction[]>('/pet/interactions')
    // return res.data
    throw new Error('use mock')
  } catch {
    return [...MOCK_INTERACTIONS]
  }
}
