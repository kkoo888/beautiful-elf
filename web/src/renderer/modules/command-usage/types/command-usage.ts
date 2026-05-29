export interface CommandUsage {
  id: number
  commandId: number
  useCount: number
  lastUsedAt: string | null
  createdAt: string
  updatedAt: string
}
