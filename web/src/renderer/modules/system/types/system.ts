/** 系统模块类型定义 */

/** 快捷键配置 */
export interface HotkeyConfig {
  id: string
  name: string
  shortcut: string
  module: string
  enabled: boolean
}

/** 默认快捷键映射（action → shortcut） */
export const DEFAULT_HOTKEYS: Record<string, string> = {
  'open-main-window': 'Ctrl+Shift+B',
  'open-command-palette': 'Ctrl+K',
  screenshot: 'Ctrl+Shift+S',
  'toggle-pet': 'Ctrl+Shift+P',
}

/** 快捷键持久化存储 Key */
export const HOTKEYS_STORAGE_KEY = 'beautiful-elf-hotkeys'

/**
 * 检测快捷键冲突
 * @param hotkeys 当前快捷键映射
 * @param key 要检测的快捷键
 * @param excludeAction 排除的动作（编辑时排除自身）
 * @returns 冲突的动作名，无冲突返回 null
 */
export function detectConflict(
  hotkeys: Record<string, string>,
  key: string,
  excludeAction?: string
): string | null {
  for (const [action, hotkey] of Object.entries(hotkeys)) {
    if (hotkey === key && action !== excludeAction) {
      return action
    }
  }
  return null
}
