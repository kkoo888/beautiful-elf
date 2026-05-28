import { useEffect } from 'react'
import { useAppStore } from '@/stores/use-app-store'
import type { ThemeMode } from '@/types'

const THEME_STORAGE_KEY = 'beautiful-elf-theme'

/**
 * 主题持久化 Hook
 * 启动时从 localStorage 恢复主题，变更时自动持久化
 * 补充 zustand/persist 在跨窗口同步时的不足
 */
export function useThemePersist() {
  const theme = useAppStore((state) => state.theme)
  const setTheme = useAppStore((state) => state.setTheme)

  // 启动时从 localStorage 恢复主题
  useEffect(() => {
    const saved = localStorage.getItem(THEME_STORAGE_KEY)
    if (saved) {
      try {
        const parsed = JSON.parse(saved) as { mode?: ThemeMode }
        if (parsed.mode) {
          setTheme(parsed.mode)
        }
      } catch {
        // 解析失败忽略
      }
    }
  }, [setTheme])

  // 主题变更时持久化
  useEffect(() => {
    localStorage.setItem(THEME_STORAGE_KEY, JSON.stringify({ mode: theme }))
  }, [theme])

  // 监听其他窗口的主题变更
  useEffect(() => {
    const handler = (e: StorageEvent) => {
      if (e.key === THEME_STORAGE_KEY && e.newValue) {
        try {
          const parsed = JSON.parse(e.newValue) as { mode?: ThemeMode }
          if (parsed.mode && parsed.mode !== useAppStore.getState().theme) {
            setTheme(parsed.mode)
          }
        } catch {
          // 解析失败忽略
        }
      }
    }
    window.addEventListener('storage', handler)
    return () => window.removeEventListener('storage', handler)
  }, [setTheme])

  return { theme, setTheme }
}
