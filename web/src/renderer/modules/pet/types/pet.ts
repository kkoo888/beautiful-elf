export type PetInteractionType = 'feed' | 'clean' | 'chat' | 'play'

export interface PetInteraction {
  id: string
  type: PetInteractionType
  effect: string
  createdAt: string
}

export const PET_INTERACTION_META: Record<
  PetInteractionType,
  { label: string; icon: string; color: string }
> = {
  feed: { label: '喂食', icon: '🍖', color: '#f97316' },
  clean: { label: '清洁', icon: '🧹', color: '#3b82f6' },
  chat: { label: '聊天', icon: '💬', color: '#22c55e' },
  play: { label: '玩耍', icon: '🎮', color: '#a855f7' },
}

// ─── 宠物设置 ───
export interface PetSettings {
  modelPath: string
  opacity: number
  decaySpeed: 'slow' | 'normal' | 'fast'
  bubbleFrequency: number
}

export const DEFAULT_PET_SETTINGS: PetSettings = {
  modelPath: '',
  opacity: 1,
  decaySpeed: 'normal',
  bubbleFrequency: 5,
}

export const DECAY_SPEED_OPTIONS = [
  { label: '慢速', value: 'slow' as const },
  { label: '正常', value: 'normal' as const },
  { label: '快速', value: 'fast' as const },
]

// ─── 宠物窗口状态 ───
export interface PetWindowInfo {
  visible: boolean
  screenshot: string | null
}

// ─── 宠物模型 ───
export interface PetModelInfo {
  name: string
  path: string
  size: number
  lastModified: number
}

// ─── Live2D 模型信息 ───
export interface Live2DModelInfo {
  name: string
  version: string
  engine: string
  expressionCount: number
  motionCount: number
  ready: boolean
}

// ─── 宠物运行状态 ───
export interface PetRuntimeStatus {
  libraryLoaded: boolean
  mouseFollow: boolean
  clickInteraction: boolean
  lipSync: boolean
  currentExpression: string
  currentMotion: string
  bubbleText: string
  motionQueueCount: number
  fps: number
}

export const FPS_OPTIONS = [
  { label: '30 FPS', value: 30 },
  { label: '60 FPS', value: 60 },
  { label: '120 FPS', value: 120 },
  { label: '无限制', value: 0 },
] as const
