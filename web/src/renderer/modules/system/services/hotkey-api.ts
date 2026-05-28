/** 快捷键 API（Mock 实现） */

import { generateId } from '@/utils'
import type { HotkeyConfig } from '../types/system'

const defaultHotkeys: HotkeyConfig[] = [
  { id: generateId(), name: '命令面板', shortcut: 'Ctrl+K', module: 'global', enabled: true },
  {
    id: generateId(),
    name: '命令面板(备选)',
    shortcut: 'Ctrl+Shift+B',
    module: 'global',
    enabled: true,
  },
  { id: generateId(), name: '新建对话', shortcut: 'Ctrl+N', module: 'chat', enabled: true },
  { id: generateId(), name: '打开设置', shortcut: 'Ctrl+,', module: 'settings', enabled: true },
  { id: generateId(), name: '截图', shortcut: 'Ctrl+Shift+S', module: 'visual', enabled: true },
  {
    id: generateId(),
    name: '打开宠物窗口',
    shortcut: 'Ctrl+Shift+P',
    module: 'pet',
    enabled: true,
  },
  { id: generateId(), name: '切换主题', shortcut: 'Ctrl+Shift+T', module: 'global', enabled: true },
]

let hotkeyStore = [...defaultHotkeys]

function delay(ms = 200): Promise<void> {
  return new Promise((r) => setTimeout(r, ms))
}

/** 获取快捷键列表 */
export async function fetchHotkeys(): Promise<HotkeyConfig[]> {
  await delay()
  return [...hotkeyStore]
}

/** 更新快捷键 */
export async function updateHotkey(id: string, shortcut: string): Promise<HotkeyConfig> {
  await delay()
  const idx = hotkeyStore.findIndex((h) => h.id === id)
  if (idx === -1) throw new Error('Hotkey not found')
  hotkeyStore[idx] = { ...hotkeyStore[idx], shortcut }
  return hotkeyStore[idx]
}

/** 重置为默认快捷键 */
export async function resetHotkeys(): Promise<HotkeyConfig[]> {
  await delay()
  hotkeyStore = [...defaultHotkeys]
  return [...hotkeyStore]
}
