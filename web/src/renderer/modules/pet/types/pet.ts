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
