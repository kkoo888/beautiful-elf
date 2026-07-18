/**
 * 材质库
 * 对齐设计文档 §3.3 材质库 + §3.4 Three.js 材质方块
 */

import * as THREE from 'three'

export interface MaterialConfig {
  id: string
  name: string
  color: number
  roughness?: number
  metalness?: number
  transparent?: boolean
  opacity?: number
  emissive?: number
  emissiveIntensity?: number
}

export const MATERIAL_CONFIGS: Record<string, MaterialConfig> = {
  // 建筑材质
  brick:     { id: 'brick',     name: '砖墙',   color: 0xb35a3f, roughness: 0.8 },
  concrete:  { id: 'concrete',  name: '混凝土', color: 0x999999, roughness: 0.9 },
  wood:      { id: 'wood',      name: '木材',   color: 0x8B4513, roughness: 0.6 },
  metal:     { id: 'metal',     name: '金属',   color: 0xcccccc, metalness: 0.9, roughness: 0.2 },
  glass:     { id: 'glass',     name: '玻璃',   color: 0x88ccff, transparent: true, opacity: 0.3 },
  stone:     { id: 'stone',     name: '石材',   color: 0x888888, roughness: 0.85 },

  // 赛博朋克材质
  neon_pink:  { id: 'neon_pink',  name: '霓虹粉', color: 0xff00ff, emissive: 0xff00ff, emissiveIntensity: 2 },
  neon_blue:  { id: 'neon_blue',  name: '霓虹蓝', color: 0x00ffff, emissive: 0x00ffff, emissiveIntensity: 2 },
  neon_green: { id: 'neon_green', name: '霓虹绿', color: 0x00ff00, emissive: 0x00ff00, emissiveIntensity: 2 },
  dark_metal: { id: 'dark_metal', name: '暗金属', color: 0x333333, metalness: 0.95, roughness: 0.1 },

  // 自然材质
  grass:  { id: 'grass',  name: '草地', color: 0x4a7c3f, roughness: 0.9 },
  water:  { id: 'water',  name: '水面', color: 0x2277cc, transparent: true, opacity: 0.6 },
  sand:   { id: 'sand',   name: '沙地', color: 0xd4b896, roughness: 0.95 },
  snow:   { id: 'snow',   name: '雪地', color: 0xeeeeff, roughness: 0.3 },
  default: { id: 'default', name: '默认', color: 0xcccccc, roughness: 0.5 },
}

// 材质缓存（避免重复创建）
const materialCache = new Map<string, THREE.Material>()

/**
 * 创建材质（带缓存）
 */
export function createMaterial(materialId: string): THREE.Material {
  const cached = materialCache.get(materialId)
  if (cached) return cached

  const config = MATERIAL_CONFIGS[materialId] ?? MATERIAL_CONFIGS.default!
  const mat = new THREE.MeshStandardMaterial({
    color: config.color,
    roughness: config.roughness ?? 0.5,
    metalness: config.metalness ?? 0,
    transparent: config.transparent ?? false,
    opacity: config.opacity ?? 1,
    emissive: config.emissive ?? 0x000000,
    emissiveIntensity: config.emissiveIntensity ?? 0,
  })

  materialCache.set(materialId, mat)
  return mat
}

export function getMaterialConfig(id: string): MaterialConfig | undefined {
  return MATERIAL_CONFIGS[id]
}

export function getAllMaterialConfigs(): MaterialConfig[] {
  return Object.values(MATERIAL_CONFIGS)
}
