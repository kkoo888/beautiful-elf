/** 快捷键 API（localStorage 持久化） */

import { generateId } from '@/utils'
import type { HotkeyConfig } from '../types/system'
import { HOTKEYS_STORAGE_KEY, DEFAULT_HOTKEYS } from '../types/system'

/** 从 localStorage 加载或使用默认值 */
function loadHotkeys(): HotkeyConfig[] {
  try {
    const saved = localStorage.getItem(HOTKEYS_STORAGE_KEY)
    if (saved) {
      const parsed: HotkeyConfig[] = JSON.parse(saved)
      if (Array.isArray(parsed) && parsed.length > 0) return parsed
    }
  } catch {
    // ignore parse errors
  }
  return getDefaultHotkeys()
}

/** 默认快捷键列表（首次使用时） */
function getDefaultHotkeys(): HotkeyConfig[] {
  return [
    {
      id: generateId(),
      name: '命令面板',
      shortcut: DEFAULT_HOTKEYS['open-command-palette'],
      module: 'global',
      enabled: true,
    },
    {
      id: generateId(),
      name: '主窗口',
      shortcut: DEFAULT_HOTKEYS['open-main-window'],
      module: 'global',
      enabled: true,
    },
    { id: generateId(), name: '新建对话', shortcut: 'Ctrl+N', module: 'chat', enabled: true },
    { id: generateId(), name: '打开设置', shortcut: 'Ctrl+,', module: 'settings', enabled: true },
    {
      id: generateId(),
      name: '截图',
      shortcut: DEFAULT_HOTKEYS['screenshot'],
      module: 'visual',
      enabled: true,
    },
    {
      id: generateId(),
      name: '打开宠物窗口',
      shortcut: DEFAULT_HOTKEYS['toggle-pet'],
      module: 'pet',
      enabled: true,
    },
    {
      id: generateId(),
      name: '切换主题',
      shortcut: 'Ctrl+Shift+T',
      module: 'global',
      enabled: true,
    },
  ]
}

/** 持久化到 localStorage */
function persist(hotkeys: HotkeyConfig[]): void {
  try {
    localStorage.setItem(HOTKEYS_STORAGE_KEY, JSON.stringify(hotkeys))
  } catch {
    // storage full or unavailable
  }
}

let hotkeyStore: HotkeyConfig[] = loadHotkeys()

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
  persist(hotkeyStore)
  return hotkeyStore[idx]
}

/** 重置为默认快捷键 */
export async function resetHotkeys(): Promise<HotkeyConfig[]> {
  await delay()
  hotkeyStore = getDefaultHotkeys()
  persist(hotkeyStore)
  return [...hotkeyStore]
}
