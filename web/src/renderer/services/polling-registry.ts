/** 轮询任务统一管理 */

export interface PollingTask {
  id: string
  module: string
  interval: number
  callback: () => Promise<void>
  enabled: boolean
}

class PollingRegistry {
  private tasks: Map<string, PollingTask> = new Map()
  private timers: Map<string, ReturnType<typeof setInterval>> = new Map()

  register(task: PollingTask): void {
    this.tasks.set(task.id, task)
    if (task.enabled) this.start(task.id)
  }

  unregister(id: string): void {
    this.stop(id)
    this.tasks.delete(id)
  }

  start(id: string): void {
    const task = this.tasks.get(id)
    if (!task) return
    // 避免重复注册
    if (this.timers.has(id)) return
    const timer = setInterval(() => {
      void task.callback()
    }, task.interval)
    this.timers.set(id, timer)
  }

  stop(id: string): void {
    const timer = this.timers.get(id)
    if (timer) {
      clearInterval(timer)
      this.timers.delete(id)
    }
  }

  pause(id: string): void {
    this.stop(id)
  }

  resume(id: string): void {
    this.start(id)
  }

  pauseAll(): void {
    for (const id of [...this.timers.keys()]) {
      this.stop(id)
    }
  }

  resumeAll(): void {
    for (const [id, task] of this.tasks) {
      if (task.enabled) this.start(id)
    }
  }

  /** 获取已注册任务数量 */
  get size(): number {
    return this.tasks.size
  }

  /** 获取活跃轮询数量 */
  get activeCount(): number {
    return this.timers.size
  }
}

export const pollingRegistry = new PollingRegistry()
