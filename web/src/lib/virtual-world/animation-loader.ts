/**
 * Animation Loader — 动画数据加载器
 *
 * 对应文档：agent-3d-building-block-system.md §3.8, §3.10
 * 加载后端生成的动画 JSON，转换为 Three.js AnimationClip。
 */
import * as THREE from 'three'

// ---------------------------------------------------------------------------
// 动画 JSON 数据格式（与后端对齐）
// ---------------------------------------------------------------------------

/** 单个骨骼的帧数据 */
export interface BoneFrameData {
  position: [number, number, number]
  rotation: [number, number, number, number]   // 四元数 [x, y, z, w]
}

/** 单帧数据 */
export interface FrameData {
  timestamp: number
  bones: Record<string, BoneFrameData>
}

/** 动画 JSON 完整结构（对应后端输出） */
export interface AnimationData {
  name: string
  duration: number
  fps: number
  boneCount: number
  frames: FrameData[]
}

// ---------------------------------------------------------------------------
// Loader
// ---------------------------------------------------------------------------

/**
 * 从后端加载动画 JSON 并解析为 Three.js AnimationClip。
 */
export async function loadAnimationFromJson(url: string): Promise<THREE.AnimationClip> {
  const resp = await fetch(url)
  if (!resp.ok) throw new Error(`Failed to load animation: ${resp.status}`)
  const data: AnimationData = await resp.json()
  return parseAnimationData(data)
}

/**
 * 将 AnimationData JSON 转换为 Three.js AnimationClip。
 *
 * 为每个骨骼创建 position 和 quaternion 的 KeyframeTrack。
 */
export function parseAnimationData(data: AnimationData): THREE.AnimationClip {
  const { name, duration, fps, frames } = data

  if (!frames.length) {
    return new THREE.AnimationClip(name, duration, [])
  }

  // 收集所有骨骼名
  const boneNames = new Set<string>()
  for (const frame of frames) {
    for (const boneName of Object.keys(frame.bones)) {
      boneNames.add(boneName)
    }
  }

  // 为每个骨骼创建 position + quaternion track
  const tracks: THREE.KeyframeTrack[] = []

  for (const boneName of boneNames) {
    const times: number[] = []
    const positions: number[] = []
    const quaternions: number[] = []

    for (const frame of frames) {
      const boneData = frame.bones[boneName]
      if (!boneData) continue

      times.push(frame.timestamp)
      positions.push(...boneData.position)
      quaternions.push(...boneData.rotation)
    }

    if (times.length === 0) continue

    // position track
    tracks.push(
      new THREE.VectorKeyframeTrack(
        `.bones[${boneName}].position`,
        times,
        positions,
        THREE.InterpolateLinear,
      ),
    )

    // quaternion track
    tracks.push(
      new THREE.QuaternionKeyframeTrack(
        `.bones[${boneName}].quaternion`,
        times,
        quaternions,
        THREE.InterpolateLinear,
      ),
    )
  }

  return new THREE.AnimationClip(name, duration, tracks)
}

// ---------------------------------------------------------------------------
// Batch Loader
// ---------------------------------------------------------------------------

/** 批量加载动画文件的元数据 */
export interface AnimationLoadResult {
  name: string
  clip: THREE.AnimationClip
  duration: number
  fps: number
  boneCount: number
}

/**
 * 批量加载动画 JSON 文件。
 */
export async function loadAnimations(
  urls: string[],
): Promise<AnimationLoadResult[]> {
  const results: AnimationLoadResult[] = []

  for (const url of urls) {
    try {
      const resp = await fetch(url)
      if (!resp.ok) continue
      const data: AnimationData = await resp.json()
      const clip = parseAnimationData(data)
      results.push({
        name: data.name,
        clip,
        duration: data.duration,
        fps: data.fps,
        boneCount: data.boneCount,
      })
    } catch (err) {
      console.warn(`Failed to load animation from ${url}:`, err)
    }
  }

  return results
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * 从 AnimationClip 提取骨骼名列表。
 */
export function getClipBoneNames(clip: THREE.AnimationClip): string[] {
  const names = new Set<string>()
  for (const track of clip.tracks) {
    const match = track.name.match(/\.bones\[(.+?)\]\./)
    if (match) names.add(match[1])
  }
  return [...names]
}

/**
 * 验证动画数据完整性。
 */
export function validateAnimationData(data: unknown): { valid: boolean; errors: string[] } {
  const errors: string[] = []

  if (!data || typeof data !== 'object') {
    return { valid: false, errors: ['Data must be an object'] }
  }

  const d = data as Record<string, unknown>

  if (typeof d.name !== 'string') errors.push('Missing "name"')
  if (typeof d.duration !== 'number' || d.duration <= 0) errors.push('Invalid "duration"')
  if (typeof d.fps !== 'number' || d.fps <= 0) errors.push('Invalid "fps"')
  if (!Array.isArray(d.frames)) errors.push('"frames" must be an array')

  return { valid: errors.length === 0, errors }
}
