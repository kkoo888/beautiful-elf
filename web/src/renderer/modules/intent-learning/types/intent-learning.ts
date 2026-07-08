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
  isSolved: number
  createdAt: string
}

export interface SkillSuggestion {
  id: string
  patternId: string
  name: string
  description: string
  ignoreCount: number
  lastFeedback: string
  createdAt: string
}

export interface AnalyzeResult {
  patternsFound: number
  patternsNew: number
  suggestionsNew: number
  patterns: Array<{ description: string; frequency: number; actions: string[]; type: string }>
  suggestions: Array<{ id: number; name: string; description: string }>
  purpose: string
  thoughts: string
}
