/**
 * 动画状态机
 * 管理动画状态转换，支持 crossFade 平滑过渡
 * 对齐设计文档 §3.9 动画状态机实现
 */

import * as THREE from 'three'

export interface AnimationState {
  name: string
  clip: THREE.AnimationClip
  loop: boolean
  speed: number
}

export interface AnimationTransition {
  from: string
  to: string
  condition: () => boolean
  duration: number // 过渡时间（秒）
}

export class AnimationStateMachine {
  private mixer: THREE.AnimationMixer
  private states: Map<string, AnimationState> = new Map()
  private actions: Map<string, THREE.AnimationAction> = new Map()
  private transitions: AnimationTransition[] = []
  private currentStateName: string | null = null
  private currentAction: THREE.AnimationAction | null = null

  constructor(mixer: THREE.AnimationMixer) {
    this.mixer = mixer
  }

  /**
   * 从根对象创建状态机
   */
  static fromRoot(root: THREE.Object3D): AnimationStateMachine {
    const mixer = new THREE.AnimationMixer(root)
    return new AnimationStateMachine(mixer)
  }

  getMixer(): THREE.AnimationMixer {
    return this.mixer
  }

  /**
   * 注册动画状态
   */
  addState(state: AnimationState): void {
    this.states.set(state.name, state)
    const action = this.mixer.clipAction(state.clip)
    action.setLoop(state.loop ? THREE.LoopRepeat : THREE.LoopOnce)
    action.setEffectiveTimeScale(state.speed)
    this.actions.set(state.name, action)
  }

  /**
   * 注册状态转换规则
   */
  addTransition(transition: AnimationTransition): void {
    this.transitions.push(transition)
  }

  /**
   * 切换到指定状态（带 crossFade 过渡）
   */
  play(stateName: string, duration?: number): void {
    const state = this.states.get(stateName)
    if (!state) {
      console.warn(`[AnimationStateMachine] state not found: ${stateName}`)
      return
    }

    const action = this.actions.get(stateName)!
    const transitionDuration = duration ?? this.findTransitionDuration(this.currentStateName, stateName)

    if (this.currentAction && this.currentAction !== action) {
      this.currentAction.crossFadeTo(action, transitionDuration)
    }

    action.reset().play()
    this.currentAction = action
    this.currentStateName = stateName
  }

  /**
   * 获取当前状态名
   */
  getCurrentState(): string | null {
    return this.currentStateName
  }

  /**
   * 更新状态机（检查自动转换 + 更新动画）
   */
  update(delta?: number): void {
    // 检查自动转换条件
    for (const transition of this.transitions) {
      if (this.currentStateName === transition.from && transition.condition()) {
        this.play(transition.to, transition.duration)
        break // 每帧最多触发一个转换
      }
    }

    this.mixer.update(delta ?? 1 / 60)
  }

  /**
   * 查找两个状态之间的过渡时间
   */
  private findTransitionDuration(from: string | null, to: string): number {
    if (!from) return 0.3
    const transition = this.transitions.find(t => t.from === from && t.to === to)
    return transition?.duration ?? 0.3
  }

  /**
   * 清理
   */
  dispose(): void {
    this.mixer.stopAllAction()
    this.states.clear()
    this.actions.clear()
    this.transitions = []
    this.currentAction = null
    this.currentStateName = null
  }
}
