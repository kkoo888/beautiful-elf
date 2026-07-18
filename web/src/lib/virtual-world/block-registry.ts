/**
 * 积木类型注册表 — 从 API 动态加载
 *
 * 方块类型数据存储在数据库中，通过 API 加载后缓存到内存。
 * 不再硬编码，保证数据库是唯一数据源。
 */

import * as THREE from 'three'

// ── 类型定义 ──

export type GeometryType = 'box' | 'sphere' | 'cylinder' | 'cone' | 'plane' | 'torus' | 'capsule' | 'circle' | 'dodecahedron' | 'icosahedron'

export type BlockCategory = 'structure' | 'decoration' | 'nature' | 'furniture' | 'light' | 'road'

export interface BlockGeometryConfig {
  type: GeometryType
  args: Record<string, number>  // 几何体参数，key-value 形式
}

export interface BlockType {
  id: string                    // block_id，如 'cube', 'wall', 'floor'
  name: string                  // 显示名称
  category: BlockCategory
  geometry: BlockGeometryConfig
  defaultMaterial: string       // 默认材质 ID
  description: string
  tags: string[]
}

// ── 运行时注册表（从 API 加载后填充）──

export const BLOCK_TYPES: Map<string, BlockType> = new Map()

let _loaded = false
let _loading = false

/**
 * 从后端 API 加载方块类型到 BLOCK_TYPES
 * 幂等：多次调用只加载一次
 */
export async function loadBlockTypes(): Promise<void> {
  if (_loaded || _loading) return
  _loading = true

  try {
    const { apiClient, extractPaginated } = await import('@/services/api-client')
    const { items } = extractPaginated(
      (await apiClient.get('/virtualworld/blocks', {
        params: { page: 1, pageSize: 500 },
      })) as unknown as { items: unknown[]; total: number },
    )

    BLOCK_TYPES.clear()
    for (const item of items as Array<{
      blockId: string
      name: string
      category: string
      geometryType: string
      geometryArgs: Record<string, number> | null
      defaultMaterial: string
      description: string
      tags: string
    }>) {
      BLOCK_TYPES.set(item.blockId, {
        id: item.blockId,
        name: item.name,
        category: item.category as BlockCategory,
        geometry: {
          type: item.geometryType as GeometryType,
          args: item.geometryArgs ?? {},
        },
        defaultMaterial: item.defaultMaterial,
        description: item.description,
        tags: item.tags ? item.tags.split(',').map((t: string) => t.trim()) : [],
      })
    }
    _loaded = true
  } catch (err) {
    console.warn('[block-registry] 加载方块类型失败:', err)
  } finally {
    _loading = false
  }
}

/**
 * 强制重新加载（用于刷新缓存）
 */
export async function reloadBlockTypes(): Promise<void> {
  _loaded = false
  await loadBlockTypes()
}

/**
 * 获取方块类型（同步，需先调 loadBlockTypes）
 */
export function getBlockType(id: string): BlockType | undefined {
  return BLOCK_TYPES.get(id)
}

/**
 * 按分类筛选方块
 */
export function getBlocksByCategory(category: BlockCategory): BlockType[] {
  return [...BLOCK_TYPES.values()].filter((b) => b.category === category)
}

/**
 * 按标签搜索方块
 */
export function getBlocksByTag(tag: string): BlockType[] {
  return [...BLOCK_TYPES.values()].filter((b) => b.tags.includes(tag))
}

/**
 * 是否已加载
 */
export function isBlockTypesLoaded(): boolean {
  return _loaded
}

// ── 几何体工厂 ──

/**
 * 根据 BlockGeometryConfig 创建 Three.js BufferGeometry
 */
export function createBlockGeometry(config: BlockGeometryConfig): THREE.BufferGeometry {
  const args = config.args
  switch (config.type) {
    case 'box':
      return new THREE.BoxGeometry(args.width ?? 1, args.height ?? 1, args.depth ?? 1)
    case 'sphere':
      return new THREE.SphereGeometry(args.radius ?? 0.5, args.widthSegments ?? 16, args.heightSegments ?? 12)
    case 'cylinder':
      return new THREE.CylinderGeometry(
        args.radiusTop ?? 0.5, args.radiusBottom ?? 0.5, args.height ?? 1,
        args.radialSegments ?? 16, args.heightSegments ?? 1,
      )
    case 'cone':
      return new THREE.ConeGeometry(args.radius ?? 0.5, args.height ?? 1, args.radialSegments ?? 16)
    case 'plane':
      return new THREE.PlaneGeometry(args.width ?? 1, args.height ?? 1)
    case 'torus':
      return new THREE.TorusGeometry(args.radius ?? 0.5, args.tube ?? 0.2, args.radialSegments ?? 16, args.tubularSegments ?? 32)
    case 'capsule':
      return new THREE.CapsuleGeometry(args.radius ?? 0.5, args.length ?? 1, args.capSegments ?? 4, args.radialSegments ?? 8)
    case 'circle':
      return new THREE.CircleGeometry(args.radius ?? 0.5, args.segments ?? 32)
    case 'dodecahedron':
      return new THREE.DodecahedronGeometry(args.radius ?? 0.5, args.detail ?? 0)
    case 'icosahedron':
      return new THREE.IcosahedronGeometry(args.radius ?? 0.5, args.detail ?? 0)
    default:
      console.warn(`[block-registry] 未知几何体类型: ${config.type}, 回退到 Box`)
      return new THREE.BoxGeometry(1, 1, 1)
  }
}
