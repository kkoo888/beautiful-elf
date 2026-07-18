/**
 * 积木类型注册表
 * 对齐设计文档 §3.1 积木类型定义 + §3.2 积木库 + §3.4 Three.js 原生基础方块
 */

import * as THREE from 'three'

// ── 积木类型定义 ──

export type GeometryType = 'box' | 'sphere' | 'cylinder' | 'cone' | 'plane' | 'torus' | 'capsule' | 'circle'

export type BlockCategory = 'structure' | 'decoration' | 'nature' | 'furniture' | 'light' | 'road'

export interface BlockGeometryConfig {
  type: GeometryType
  args: number[] // 几何体参数，顺序对齐 Three.js 构造函数
}

export interface BlockType {
  id: string                    // 唯一标识，如 'cube', 'wall', 'floor'
  name: string                  // 显示名称
  category: BlockCategory
  geometry: BlockGeometryConfig
  defaultMaterial: string       // 默认材质 ID
  size: [number, number, number] // 占用空间 [宽, 高, 深]（网格单位）
  description: string
  tags: string[]
}

// ── 积木库 ──

export const BLOCK_TYPES: Record<string, BlockType> = {
  // 结构类
  cube: {
    id: 'cube', name: '方块', category: 'structure',
    geometry: { type: 'box', args: [1, 1, 1] },
    defaultMaterial: 'brick', size: [1, 1, 1],
    description: '基础方块', tags: ['基础', '建筑'],
  },
  wall: {
    id: 'wall', name: '墙壁', category: 'structure',
    geometry: { type: 'box', args: [1, 3, 0.2] },
    defaultMaterial: 'brick', size: [1, 3, 1],
    description: '墙体', tags: ['建筑', '墙'],
  },
  floor: {
    id: 'floor', name: '地板', category: 'structure',
    geometry: { type: 'box', args: [1, 0.1, 1] },
    defaultMaterial: 'wood', size: [1, 1, 1],
    description: '地板', tags: ['建筑', '地面'],
  },
  roof_slope: {
    id: 'roof_slope', name: '斜屋顶', category: 'structure',
    geometry: { type: 'cone', args: [0.7, 1, 4] },
    defaultMaterial: 'brick', size: [1, 1, 1],
    description: '斜屋顶', tags: ['建筑', '屋顶'],
  },
  pillar: {
    id: 'pillar', name: '柱子', category: 'structure',
    geometry: { type: 'cylinder', args: [0.15, 0.15, 3, 8] },
    defaultMaterial: 'concrete', size: [1, 3, 1],
    description: '支撑柱', tags: ['建筑', '柱'],
  },
  window: {
    id: 'window', name: '窗户', category: 'structure',
    geometry: { type: 'box', args: [0.8, 1, 0.05] },
    defaultMaterial: 'glass', size: [1, 1, 1],
    description: '透明窗', tags: ['建筑', '窗'],
  },

  // 装饰类
  tree_trunk: {
    id: 'tree_trunk', name: '树干', category: 'decoration',
    geometry: { type: 'cylinder', args: [0.1, 0.1, 2, 8] },
    defaultMaterial: 'wood', size: [1, 2, 1],
    description: '树干', tags: ['植物', '树'],
  },
  tree_canopy: {
    id: 'tree_canopy', name: '树冠', category: 'decoration',
    geometry: { type: 'sphere', args: [0.8, 16, 16] },
    defaultMaterial: 'grass', size: [2, 2, 2],
    description: '树叶', tags: ['植物', '树'],
  },
  bush: {
    id: 'bush', name: '灌木', category: 'decoration',
    geometry: { type: 'sphere', args: [0.4, 12, 12] },
    defaultMaterial: 'grass', size: [1, 1, 1],
    description: '绿植', tags: ['植物'],
  },
  rock: {
    id: 'rock', name: '石头', category: 'decoration',
    geometry: { type: 'sphere', args: [0.3, 8, 6] },
    defaultMaterial: 'stone', size: [1, 1, 1],
    description: '自然石块', tags: ['自然', '石'],
  },
  fence: {
    id: 'fence', name: '栅栏', category: 'decoration',
    geometry: { type: 'box', args: [1, 0.8, 0.05] },
    defaultMaterial: 'wood', size: [1, 1, 1],
    description: '围栏', tags: ['建筑', '围栏'],
  },
  lamp_post: {
    id: 'lamp_post', name: '路灯', category: 'light',
    geometry: { type: 'cylinder', args: [0.03, 0.03, 3, 6] },
    defaultMaterial: 'metal', size: [1, 3, 1],
    description: '街灯', tags: ['灯光', '路灯'],
  },

  // 自然类
  water: {
    id: 'water', name: '水面', category: 'nature',
    geometry: { type: 'plane', args: [1, 1] },
    defaultMaterial: 'water', size: [1, 1, 1],
    description: '水面', tags: ['自然', '水'],
  },
  grass_block: {
    id: 'grass_block', name: '草地', category: 'nature',
    geometry: { type: 'box', args: [1, 0.1, 1] },
    defaultMaterial: 'grass', size: [1, 1, 1],
    description: '草地', tags: ['自然', '地面'],
  },
}

// ── 工具函数 ──

export function getBlockType(id: string): BlockType | undefined {
  return BLOCK_TYPES[id]
}

export function getBlocksByCategory(category: BlockCategory): BlockType[] {
  return Object.values(BLOCK_TYPES).filter(b => b.category === category)
}

export function getAllBlockTypes(): BlockType[] {
  return Object.values(BLOCK_TYPES)
}

/**
 * 创建积木几何体
 */
export function createBlockGeometry(config: BlockGeometryConfig): THREE.BufferGeometry {
  switch (config.type) {
    case 'box':
      return new THREE.BoxGeometry(...(config.args as [number, number, number]))
    case 'sphere':
      return new THREE.SphereGeometry(...(config.args as [number, number, number]))
    case 'cylinder':
      return new THREE.CylinderGeometry(...(config.args as [number, number, number, number]))
    case 'cone':
      return new THREE.ConeGeometry(...(config.args as [number, number, number]))
    case 'plane':
      return new THREE.PlaneGeometry(...(config.args as [number, number]))
    case 'torus':
      return new THREE.TorusGeometry(...(config.args as [number, number, number, number]))
    case 'circle':
      return new THREE.CircleGeometry(...(config.args as [number, number]))
    default:
      return new THREE.BoxGeometry(1, 1, 1)
  }
}
