export interface IntentCorrection {
  id: string
  originalIntent: string
  correctModule: string
  createdAt: string
}

export interface BehaviorPattern {
  id: string
  description: string
  frequency: number
  actions: string[]
}

export interface SkillSuggestion {
  id: string
  patternId: string
  name: string
  description: string
  createdAt: string
}
