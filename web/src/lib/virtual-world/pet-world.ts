/**
 * Pet World — 前端集成入口
 *
 * 对应文档：agent-3d-building-block-system.md §6
 * 整合场景构建器 + 动画系统 + 工具注册，提供统一 API。
 */
import * as THREE from 'three'
import { SceneBuilder } from './scene-builder'
import { AnimationManager } from './animation-manager'
import { AnimationStateMachine, type AnimationState, type AnimationTransition } from './animation-state-machine'
import { ScriptExecutor, type SceneBuildScript, type ExecutionResult } from './script-executor'
import { createDefaultToolRegistry, type SceneToolRegistry } from './scene-tools'
import { disposeMaterialCache } from './materials'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface PetWorldOptions {
  /** Three.js 场景 */
  scene: THREE.Scene
  /** 宠物模型（可选，用于动画绑定） */
  petModel?: THREE.Object3D
  /** 自定义工具注册表（可选） */
  toolRegistry?: SceneToolRegistry
}

// ---------------------------------------------------------------------------
// PetWorld — 统一入口
// ---------------------------------------------------------------------------

/**
 * PetWorld 整合了场景构建、动画系统和 Agent 工具。
 *
 * 使用方式：
 * ```ts
 * const world = new PetWorld({ scene })
 * // 执行构建脚本
 * const result = world.executeScript(script)
 * // 播放动画
 * world.playAnimation('idle')
 * // 每帧更新
 * world.update(delta)
 * ```
 */
export class PetWorld {
  /** 场景构建器 */
  readonly sceneBuilder: SceneBuilder
  /** 构建脚本执行器 */
  readonly scriptExecutor: ScriptExecutor
  /** 工具注册表 */
  readonly toolRegistry: SceneToolRegistry

  /** 动画管理器（管理 AnimationMixer + clip 库） */
  animationManager: AnimationManager | null
  /** 动画状态机（管理状态转换） */
  stateMachine: AnimationStateMachine | null

  private scene: THREE.Scene
  private petModel: THREE.Object3D | null

  constructor(options: PetWorldOptions) {
    this.scene = options.scene
    this.petModel = options.petModel ?? null
    this.sceneBuilder = new SceneBuilder(options.scene)
    this.toolRegistry = options.toolRegistry ?? createDefaultToolRegistry()
    this.scriptExecutor = new ScriptExecutor(this.sceneBuilder, this.toolRegistry)

    // 初始化动画系统（如果有宠物模型）
    if (this.petModel) {
      this.animationManager = new AnimationManager(this.petModel)
      this.stateMachine = new AnimationStateMachine(this.animationManager.getMixer())
    } else {
      this.animationManager = null
      this.stateMachine = null
    }
  }

  // -------------------------------------------------------------------------
  // 场景操作
  // -------------------------------------------------------------------------

  /** 执行构建脚本 */
  executeScript(script: SceneBuildScript): ExecutionResult {
    return this.scriptExecutor.execute(script)
  }

  /** 加载并执行构建脚本（从 URL） */
  async loadAndExecuteScript(url: string): Promise<ExecutionResult> {
    const resp = await fetch(url)
    if (!resp.ok) throw new Error(`Failed to load script: ${resp.status}`)
    const script = (await resp.json()) as SceneBuildScript
    return this.scriptExecutor.execute(script)
  }

  /** 清空场景 */
  clearScene(): void {
    this.sceneBuilder.clearScene()
  }

  /** 获取场景信息 */
  getSceneInfo(): { blockCount: number } {
    return { blockCount: this.sceneBuilder.size }
  }

  // -------------------------------------------------------------------------
  // 动画操作
  // -------------------------------------------------------------------------

  /** 加载动画文件（BVH/FBX/JSON） */
  async loadAnimation(url: string, name?: string): Promise<THREE.AnimationClip> {
    if (!this.animationManager) throw new Error('No pet model bound, cannot load animation')
    return this.animationManager.loadAnimation(url, name)
  }

  /** 注册动画状态到状态机 */
  addAnimationState(state: AnimationState): void {
    if (!this.stateMachine) throw new Error('No pet model bound, cannot add animation state')
    this.stateMachine.addState(state)
  }

  /** 注册动画转换 */
  addAnimationTransition(transition: AnimationTransition): void {
    if (!this.stateMachine) throw new Error('No pet model bound, cannot add animation transition')
    this.stateMachine.addTransition(transition)
  }

  /** 播放动画（通过状态机或直接播放） */
  playAnimation(name: string, options?: { duration?: number }): void {
    if (this.stateMachine) {
      this.stateMachine.play(name, options?.duration)
    } else if (this.animationManager) {
      this.animationManager.play(name)
    } else {
      throw new Error('No animation system available')
    }
  }

  /** 停止动画 */
  stopAnimation(): void {
    this.animationManager?.stop()
  }

  // -------------------------------------------------------------------------
  // 每帧更新
  // -------------------------------------------------------------------------

  /** 每帧调用，更新动画系统 */
  update(delta: number): void {
    // 更新动画状态机（包含 mixer.update）
    if (this.stateMachine) {
      this.stateMachine.update(delta)
    } else if (this.animationManager) {
      this.animationManager.update(delta)
    }
  }

  // -------------------------------------------------------------------------
  // 生命周期
  // -------------------------------------------------------------------------

  /** 绑定宠物模型（延迟绑定） */
  bindPetModel(model: THREE.Object3D): void {
    this.petModel = model
    // 重新创建动画系统
    this.animationManager = new AnimationManager(model)
    this.stateMachine = new AnimationStateMachine(this.animationManager.getMixer())
  }

  /** 释放所有资源 */
  dispose(): void {
    this.sceneBuilder.clearScene()
    this.animationManager?.dispose()
    disposeMaterialCache()
  }
}
