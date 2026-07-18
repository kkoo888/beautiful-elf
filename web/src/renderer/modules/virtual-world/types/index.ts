export interface VirtualWorldScene {
  id: number
  name: string
  description: string
  width: number
  depth: number
  height: number
  ambientColor: string
  skyColor: string
  timeOfDay: number
  isActive: boolean
  createdAt: string
  updatedAt: string
}

export interface VirtualWorldBlock {
  id: number
  blockId: string
  name: string
  category: string
  geometryType: string
  geometryArgs: Record<string, unknown>
  defaultMaterial: string
  description: string
  tags: string
  sortOrder: number
  createdAt: string
  updatedAt: string
}

export interface VirtualWorldSceneBlock {
  id: number
  sceneId: number
  blockId: string
  posX: number
  posY: number
  posZ: number
  rotationY: number
  material: string
  createdAt: string
  updatedAt: string
}

export interface VirtualWorldSceneFormData {
  name: string
  description?: string
  width?: number
  depth?: number
  height?: number
  ambientColor?: string
  skyColor?: string
  timeOfDay?: number
}

export interface VirtualWorldBlockFormData {
  blockId: string
  name: string
  category?: string
  geometryType?: string
  geometryArgs?: Record<string, unknown>
  defaultMaterial?: string
  description?: string
  tags?: string
}
