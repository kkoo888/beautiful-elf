/**
 * 动画管理器
 * 负责加载、播放、停止动画，维护 clip 库
 * 对齐设计文档 §3.8 动画数据格式规范
 */

import * as THREE from 'three'

export interface PlayOptions {
  loop?: boolean
  speed?: number
  fadeIn?: number // 过渡时间（秒）
}

export class AnimationManager {
  private mixer: THREE.AnimationMixer
  private clips: Map<string, THREE.AnimationClip> = new Map()
  private currentAction: THREE.AnimationAction | null = null
  private currentClipName: string | null = null

  constructor(root: THREE.Object3D) {
    this.mixer = new THREE.AnimationMixer(root)
  }

  getMixer(): THREE.AnimationMixer {
    return this.mixer
  }

  /**
   * 注册一个 AnimationClip
   */
  addClip(name: string, clip: THREE.AnimationClip): void {
    this.clips.set(name, clip)
  }

  /**
   * 从 JSON 数据加载动画（对齐 §3.8 AnimationData 格式）
   */
  loadFromJson(data: {
    name: string
    duration: number
    fps: number
    frames: Array<{
      timestamp: number
      bones: Record<string, {
        position: [number, number, number]
        rotation: [number, number, number, number]
      }>
    }>
  }): void {
    const tracks: THREE.KeyframeTrack[] = []

    // 收集所有骨骼名
    const boneNames = new Set<string>()
    for (const frame of data.frames) {
      for (const name of Object.keys(frame.bones)) {
        boneNames.add(name)
      }
    }

    // 为每个骨骼创建 position + rotation track
    for (const boneName of boneNames) {
      const times: number[] = []
      const positions: number[] = []
      const rotations: number[] = []

      for (const frame of data.frames) {
        const boneData = frame.bones[boneName]
        if (!boneData) continue
        times.push(frame.timestamp)
        positions.push(...boneData.position)
        rotations.push(...boneData.rotation)
      }

      if (times.length === 0) continue

      tracks.push(
        new THREE.VectorKeyframeTrack(`.bones[${boneName}].position`, times, positions),
        new THREE.QuaternionKeyframeTrack(`.bones[${boneName}].quaternion`, times, rotations),
      )
    }

    const clip = new THREE.AnimationClip(data.name, data.duration, tracks)
    this.clips.set(data.name, clip)
  }

  /**
   * 播放指定动画
   */
  play(clipName: string, options: PlayOptions = {}): void {
    const clip = this.clips.get(clipName)
    if (!clip) {
      console.warn(`[AnimationManager] clip not found: ${clipName}`)
      return
    }

    const action = this.mixer.clipAction(clip)
    action.setLoop(options.loop ?? true ? THREE.LoopRepeat : THREE.LoopOnce)
    action.setEffectiveTimeScale(options.speed ?? 1.0)

    if (this.currentAction && this.currentAction !== action) {
      const fadeIn = options.fadeIn ?? 0.3
      this.currentAction.crossFadeTo(action, fadeIn)
    }

    action.reset().play()
    this.currentAction = action
    this.currentClipName = clipName
  }

  /**
   * 停止当前动画
   */
  stop(): void {
    if (this.currentAction) {
      this.currentAction.stop()
      this.currentAction = null
      this.currentClipName = null
    }
  }

  /**
   * 获取当前播放的动画名
   */
  getCurrentClipName(): string | null {
    return this.currentClipName
  }

  /**
   * 获取已加载的动画列表
   */
  getClipNames(): string[] {
    return Array.from(this.clips.keys())
  }

  /**
   * 每帧更新
   */
  update(delta?: number): void {
    this.mixer.update(delta ?? 1 / 60)
  }

  /**
   * 清理资源
   */
  dispose(): void {
    this.mixer.stopAllAction()
    this.clips.clear()
    this.currentAction = null
    this.currentClipName = null
  }
}
