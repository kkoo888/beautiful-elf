import { create } from 'zustand'
import type { Command } from '@/types'

interface CommandState {
  /** 已注册的命令列表 */
  commands: Command[]
  /** 命令面板是否打开 */
  isOpen: boolean

  /** 注册命令（支持模块动态注册） */
  registerCommand: (command: Command) => void
  /** 批量注册命令 */
  registerCommands: (commands: Command[]) => void
  /** 注销模块的所有命令 */
  unregisterModule: (module: string) => void
  /** 更新命令使用统计 */
  recordUsage: (commandId: string) => void
  /** 打开命令面板 */
  open: () => void
  /** 关闭命令面板 */
  close: () => void
  /** 切换命令面板 */
  toggle: () => void
}

export const useCommandStore = create<CommandState>((set, get) => ({
  commands: [],
  isOpen: false,

  registerCommand: (command) => {
    const { commands } = get()
    // 避免重复注册
    if (commands.some((c) => c.id === command.id)) return
    set({ commands: [...commands, command] })
  },

  registerCommands: (newCommands) => {
    const { commands } = get()
    const existingIds = new Set(commands.map((c) => c.id))
    const unique = newCommands.filter((c) => !existingIds.has(c.id))
    set({ commands: [...commands, ...unique] })
  },

  unregisterModule: (module) => {
    set((state) => ({
      commands: state.commands.filter((c) => c.module !== module),
    }))
  },

  recordUsage: (commandId) => {
    set((state) => ({
      commands: state.commands.map((c) =>
        c.id === commandId ? { ...c, useCount: c.useCount + 1, lastUsedAt: Date.now() } : c
      ),
    }))
  },

  open: () => set({ isOpen: true }),
  close: () => set({ isOpen: false }),
  toggle: () => set((state) => ({ isOpen: !state.isOpen })),
}))
