/**
 * 场景构建器
 * 在 Three.js 中渲染积木场景，使用 InstancedMesh 优化批量渲染
 * 对齐设计文档 §3.5 最小可用方块集 + §3.6 乐高物理原理对齐
 */

import * as THREE from 'three'
import { BLOCK_TYPES, type BlockType, createBlockGeometry } from './block-registry'
import { createMaterial } from './materials'

// ── 类型定义 ──

export interface SceneBlockData {
  blockId: string
  posX: number
  posY: number
  posZ: number
  rotationY?: number
  material?: string
}

interface PlacedBlock {
  blockType: BlockType
  batchKey: string
  instanceIndex: number
}

interface Batch {
  mesh: THREE.InstancedMesh
  count: number
  capacity: number
  materialId: string
  rotationY: number
}

// ── 工具函数 ──

function blockKey(x: number, y: number, z: number): string {
  return `${x},${y},${z}`
}

function batchKey(blockId: string, materialId: string, rotationY: number): string {
  return `${blockId}|${materialId}|${rotationY}`
}

function assertInteger(x: number, y: number, z: number): void {
  if (!Number.isInteger(x) || !Number.isInteger(y) || !Number.isInteger(z)) {
    throw new Error(`坐标必须为整数: (${x}, ${y}, ${z})`)
  }
}

function assertRotation(rotationY: number): void {
  if (![0, 90, 180, 270].includes(rotationY)) {
    throw new Error(`旋转只允许 0/90/180/270 度: ${rotationY}`)
  }
}

// ── 默认矩阵 ──

const _matrix = new THREE.Matrix4()
const _position = new THREE.Vector3()
const _quaternion = new THREE.Quaternion()
const _scale = new THREE.Vector3(1, 1, 1)

// ── SceneBuilder ──

const INITIAL_INSTANCE_CAPACITY = 1024

export class SceneBuilder {
  private scene: THREE.Scene
  private blocks: Map<string, PlacedBlock> = new Map()
  private batches: Map<string, Batch> = new Map()
  private group: THREE.Group

  constructor(scene: THREE.Scene) {
    this.scene = scene
    this.group = new THREE.Group()
    this.group.name = 'virtual-world-blocks'
    this.scene.add(this.group)
  }

  /**
   * 放置积木到场景
   */
  placeBlock(
    blockId: string,
    x: number,
    y: number,
    z: number,
    rotationY = 0,
    materialId?: string,
  ): void {
    assertInteger(x, y, z)
    assertRotation(rotationY)

    const key = blockKey(x, y, z)
    const blockType = BLOCK_TYPES[blockId]
    if (!blockType) throw new Error(`未知方块类型: ${blockId}`)

    const matId = materialId ?? blockType.defaultMaterial

    // 如果该位置已有积木，先移除
    if (this.blocks.has(key)) {
      this.removeBlock(x, y, z)
    }

    // 获取或创建批次
    const bKey = batchKey(blockId, matId, rotationY)
    let batch = this.batches.get(bKey)
    if (!batch) {
      batch = this.createBatch(blockType, matId, rotationY)
      this.batches.set(bKey, batch)
    }

    // 扩容检查
    if (batch.count >= batch.capacity) {
      this.growBatch(batch)
    }

    // 设置实例矩阵
    _position.set(x, y, z)
    _quaternion.setFromAxisAngle(new THREE.Vector3(0, 1, 0), (rotationY * Math.PI) / 180)
    _matrix.compose(_position, _quaternion, _scale)
    batch.mesh.setMatrixAt(batch.count, _matrix)
    batch.mesh.instanceMatrix.needsUpdate = true

    // 记录
    this.blocks.set(key, {
      blockType,
      batchKey: bKey,
      instanceIndex: batch.count,
    })

    batch.count++
  }

  /**
   * 移除指定位置的积木
   */
  removeBlock(x: number, y: number, z: number): boolean {
    assertInteger(x, y, z)
    const key = blockKey(x, y, z)
    const block = this.blocks.get(key)
    if (!block) return false

    const batch = this.batches.get(block.batchKey)
    if (!batch) return false

    // swap-with-last 保持 buffer 紧凑
    const lastIndex = batch.count - 1
    if (block.instanceIndex !== lastIndex) {
      // 把最后一个实例移到被删除的位置
      batch.mesh.getMatrixAt(lastIndex, _matrix)
      batch.mesh.setMatrixAt(block.instanceIndex, _matrix)

      // 更新被移动积木的引用
      for (const [, b] of this.blocks) {
        if (b.batchKey === block.batchKey && b.instanceIndex === lastIndex) {
          b.instanceIndex = block.instanceIndex
          break
        }
      }
    }

    batch.count--
    batch.mesh.instanceMatrix.needsUpdate = true
    batch.mesh.count = batch.count

    this.blocks.delete(key)
    return true
  }

  /**
   * 清空场景
   */
  clearScene(): void {
    for (const batch of this.batches.values()) {
      batch.mesh.geometry.dispose()
      if (Array.isArray(batch.mesh.material)) {
        batch.mesh.material.forEach(m => m.dispose())
      } else {
        batch.mesh.material.dispose()
      }
      this.group.remove(batch.mesh)
    }
    this.batches.clear()
    this.blocks.clear()
  }

  /**
   * 从数据批量加载
   */
  loadFromBlocks(blocks: SceneBlockData[]): void {
    this.clearScene()
    for (const b of blocks) {
      this.placeBlock(b.blockId, b.posX, b.posY, b.posZ, b.rotationY ?? 0, b.material)
    }
  }

  /**
   * 查询指定位置的积木
   */
  getBlockAt(x: number, y: number, z: number): { blockType: BlockType } | undefined {
    const block = this.blocks.get(blockKey(x, y, z))
    if (!block) return undefined
    return { blockType: block.blockType }
  }

  /**
   * 获取所有积木数据（用于序列化保存）
   */
  getAllBlocks(): SceneBlockData[] {
    const result: SceneBlockData[] = []
    for (const [key, block] of this.blocks) {
      const [x, y, z] = key.split(',').map(Number)
      const batch = this.batches.get(block.batchKey)
      result.push({
        blockId: block.blockType.id,
        posX: x, posY: y, posZ: z,
        rotationY: batch?.rotationY ?? 0,
        material: batch?.materialId ?? '',
      })
    }
    return result
  }

  /**
   * 获取积木总数
   */
  getBlockCount(): number {
    return this.blocks.size
  }

  // ── 内部方法 ──

  private createBatch(blockType: BlockType, materialId: string, rotationY: number): Batch {
    const geometry = createBlockGeometry(blockType.geometry)
    const material = createMaterial(materialId)

    // 旋转几何体（避免每个实例都旋转）
    if (rotationY !== 0) {
      geometry.rotateY((rotationY * Math.PI) / 180)
    }

    const mesh = new THREE.InstancedMesh(geometry, material, INITIAL_INSTANCE_CAPACITY)
    mesh.count = 0
    mesh.castShadow = true
    mesh.receiveShadow = true
    this.group.add(mesh)

    return {
      mesh,
      count: 0,
      capacity: INITIAL_INSTANCE_CAPACITY,
      materialId,
      rotationY,
    }
  }

  private growBatch(batch: Batch): void {
    const newCapacity = batch.capacity * 2
    const newMesh = new THREE.InstancedMesh(
      batch.mesh.geometry.clone(),
      batch.mesh.material,
      newCapacity,
    )
    newMesh.count = batch.count

    // 复制已有实例矩阵
    for (let i = 0; i < batch.count; i++) {
      batch.mesh.getMatrixAt(i, _matrix)
      newMesh.setMatrixAt(i, _matrix)
    }
    newMesh.instanceMatrix.needsUpdate = true
    newMesh.castShadow = true
    newMesh.receiveShadow = true

    this.group.remove(batch.mesh)
    batch.mesh.dispose()
    this.group.add(newMesh)

    batch.mesh = newMesh
    batch.capacity = newCapacity
  }
}
