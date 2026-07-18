/**
 * Bone Retargeter — 骨骼映射 + 动画重定向
 *
 * 对应文档：agent-3d-building-block-system.md §3.11, §3.13
 * 实现 Mixamo↔PMX 骨骼映射 + AnimationClip 重定向
 */
import * as THREE from 'three'

// ---------------------------------------------------------------------------
// 骨骼映射表
// ---------------------------------------------------------------------------

/** Mixamo 标准骨骼名 → PMX/MMD 骨骼名 */
export const MIXAMO_TO_PMX: Record<string, string> = {
  // 躯干
  Hips: '下半身',
  Spine: '上半身',
  Spine1: '上半身1',
  Spine2: '上半身2',
  Neck: '首',
  Head: '頭',

  // 左臂
  LeftShoulder: '左肩',
  LeftArm: '左腕',
  LeftForeArm: '左ひじ',
  LeftHand: '左手首',

  // 右臂
  RightShoulder: '右肩',
  RightArm: '右腕',
  RightForeArm: '右ひじ',
  RightHand: '右首首',

  // 左腿
  LeftUpLeg: '左足',
  LeftLeg: '左ひざ',
  LeftFoot: '左足首',
  LeftToeBase: '左つま先',

  // 右腿
  RightUpLeg: '右足',
  RightLeg: '右ひざ',
  RightFoot: '右足首',
  RightToeBase: '右つま先',

  // 手指
  LeftHandThumb1: '左親指1',
  LeftHandThumb2: '左親指2',
  LeftHandIndex1: '左人指1',
  LeftHandMiddle1: '左中指1',
  RightHandThumb1: '右親指1',
  RightHandIndex1: '右人指1',
  RightHandMiddle1: '右中指1',
}

/** Mixamo 标准骨骼名 → VRM 标准骨骼名 */
export const MIXAMO_TO_VRM: Record<string, string> = {
  Hips: 'hips',
  Spine: 'spine',
  Spine1: 'chest',
  Spine2: 'upperChest',
  Neck: 'neck',
  Head: 'head',
  LeftShoulder: 'leftShoulder',
  LeftArm: 'leftUpperArm',
  LeftForeArm: 'leftLowerArm',
  LeftHand: 'leftHand',
  RightShoulder: 'rightShoulder',
  RightArm: 'rightUpperArm',
  RightForeArm: 'rightLowerArm',
  RightHand: 'rightHand',
  LeftUpLeg: 'leftUpperLeg',
  LeftLeg: 'leftLowerLeg',
  LeftFoot: 'leftFoot',
  RightUpLeg: 'rightUpperLeg',
  RightLeg: 'rightLowerLeg',
  RightFoot: 'rightFoot',
}

/** 反向映射：PMX → Mixamo */
export const PMX_TO_MIXAMO: Record<string, string> = Object.fromEntries(
  Object.entries(MIXAMO_TO_PMX).map(([k, v]) => [v, k]),
)

/** 反向映射：VRM → Mixamo */
export const VRM_TO_MIXAMO: Record<string, string> = Object.fromEntries(
  Object.entries(MIXAMO_TO_VRM).map(([k, v]) => [v, k]),
)

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type BoneMapping = Record<string, string>

export interface RetargetOptions {
  /** 骨骼名映射：sourceBoneName → targetBoneName */
  boneMap: BoneMapping
  /** 是否保留未映射的轨道（默认 false，丢弃） */
  keepUnmapped?: boolean
}

// ---------------------------------------------------------------------------
// Core: AnimationClip 重定向
// ---------------------------------------------------------------------------

/**
 * 将源 AnimationClip 的骨骼名替换为目标骨骼名。
 *
 * 例如：Mixamo clip → PMX clip（使用 MIXAMO_TO_PMX 映射）
 *
 * Three.js track 命名格式：`.bones[BoneName].position` / `.bones[BoneName].quaternion`
 */
export function retargetClip(
  sourceClip: THREE.AnimationClip,
  options: RetargetOptions,
): THREE.AnimationClip {
  const { boneMap, keepUnmapped = false } = options

  const newTracks: THREE.KeyframeTrack[] = []

  for (const track of sourceClip.tracks) {
    const parsed = parseTrackName(track.name)
    if (!parsed) {
      // 非骨骼轨道（如 morphTargetInfluences），按 keepUnmapped 决定
      if (keepUnmapped) newTracks.push(track)
      continue
    }

    const targetBoneName = boneMap[parsed.boneName]
    if (!targetBoneName) {
      if (keepUnmapped) newTracks.push(track)
      continue
    }

    // 创建新轨道，替换骨骼名
    const newTrack = track.clone()
    newTrack.name = `.bones[${targetBoneName}].${parsed.property}`
    newTracks.push(newTrack)
  }

  return new THREE.AnimationClip(
    sourceClip.name,
    sourceClip.duration,
    newTracks,
  )
}

/**
 * 便捷函数：Mixamo clip → PMX clip
 */
export function retargetMixamoToPmx(
  clip: THREE.AnimationClip,
): THREE.AnimationClip {
  return retargetClip(clip, { boneMap: MIXAMO_TO_PMX })
}

/**
 * 便捷函数：Mixamo clip → VRM clip
 */
export function retargetMixamoToVrm(
  clip: THREE.AnimationClip,
): THREE.AnimationClip {
  return retargetClip(clip, { boneMap: MIXAMO_TO_VRM })
}

/**
 * PMX clip → Mixamo clip（反向）
 */
export function retargetPmxToMixamo(
  clip: THREE.AnimationClip,
): THREE.AnimationClip {
  return retargetClip(clip, { boneMap: PMX_TO_MIXAMO })
}

// ---------------------------------------------------------------------------
// Skeleton 辅助
// ---------------------------------------------------------------------------

/**
 * 从 Skeleton 中提取骨骼名列表。
 */
export function getBoneNames(skeleton: THREE.Skeleton): string[] {
  return skeleton.bones.map(b => b.name)
}

/**
 * 检查目标骨骼是否兼容映射表（所有目标骨骼名都存在于 skeleton 中）。
 */
export function checkCompatibility(
  boneMap: BoneMapping,
  targetSkeleton: THREE.Skeleton,
): { compatible: boolean; missing: string[] } {
  const targetNames = new Set(getBoneNames(targetSkeleton))
  const missing: string[] = []

  for (const targetName of new Set(Object.values(boneMap))) {
    if (!targetNames.has(targetName)) {
      missing.push(targetName)
    }
  }

  return { compatible: missing.length === 0, missing }
}

/**
 * PMX → VRM 映射（两跳：PMX → Mixamo → VRM）
 */
export function pmxToVrm(pmxBoneName: string): string | null {
  const mixamoName = PMX_TO_MIXAMO[pmxBoneName]
  if (!mixamoName) return null
  return MIXAMO_TO_VRM[mixamoName] ?? null
}

/**
 * VRM → PMX 映射（两跳：VRM → Mixamo → PMX）
 */
export function vrmToPmx(vrmBoneName: string): string | null {
  const mixamoName = VRM_TO_MIXAMO[vrmBoneName]
  if (!mixamoName) return null
  return MIXAMO_TO_PMX[mixamoName] ?? null
}

// ---------------------------------------------------------------------------
// 内部工具函数
// ---------------------------------------------------------------------------

interface ParsedTrackName {
  boneName: string
  property: string   // position / quaternion / scale
}

/**
 * 解析 Three.js 动画轨道名。
 * 格式：`.bones[BoneName].position` 或 `.bones[BoneName].quaternion`
 */
function parseTrackName(name: string): ParsedTrackName | null {
  const match = name.match(/\.bones\[(.+?)\]\.(.+)/)
  if (!match) return null
  return { boneName: match[1], property: match[2] }
}
