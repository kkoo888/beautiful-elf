import { useCallback, useEffect } from 'react'
import { useAppStore } from '@/stores/use-app-store'
import type { ThemeMode } from '@/types'

/**
 * 主题切换 Hook
 * 封装主题状态读写 + DOM 属性同步
 */
export function useTheme() {
  const theme = useAppStore((state) => state.theme)
  const setTheme = useAppStore((state) => state.setTheme)
  const toggleTheme = useAppStore((state) => state.toggleTheme)

  // 应用主题到 DOM
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    if (theme === 'dark') {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }, [theme])

  // 切换到指定主题
  const switchTheme = useCallback(
    (newTheme: ThemeMode) => {
      setTheme(newTheme)
    },
    [setTheme]
  )

  return {
    theme,
    isDark: theme === 'dark',
    setTheme: switchTheme,
    toggleTheme,
  }
}
