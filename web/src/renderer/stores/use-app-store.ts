import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { ThemeMode } from '@/types'

interface AppState {
  // 主题
  theme: ThemeMode
  setTheme: (theme: ThemeMode) => void
  toggleTheme: () => void

  // 侧边栏
  sidebarCollapsed: boolean
  setSidebarCollapsed: (collapsed: boolean) => void
  toggleSidebar: () => void

  // 网络状态
  isOnline: boolean
  setIsOnline: (online: boolean) => void

  // 当前模块
  currentModule: string
  setCurrentModule: (module: string) => void
}

/**
 * 全局 UI 状态 Store
 * 管理侧边栏折叠、主题、网络状态等
 * 主题和侧边栏状态持久化到 localStorage
 */
export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      // 主题
      theme: 'light',
      setTheme: (theme) => set({ theme }),
      toggleTheme: () =>
        set((state) => ({
          theme: state.theme === 'light' ? 'dark' : 'light'
        })),

      // 侧边栏
      sidebarCollapsed: false,
      setSidebarCollapsed: (sidebarCollapsed) => set({ sidebarCollapsed }),
      toggleSidebar: () =>
        set((state) => ({
          sidebarCollapsed: !state.sidebarCollapsed
        })),

      // 网络状态
      isOnline: navigator.onLine,
      setIsOnline: (isOnline) => set({ isOnline }),

      // 当前模块
      currentModule: 'chat',
      setCurrentModule: (currentModule) => set({ currentModule })
    }),
    {
      name: 'beautiful-elf:app',
      partialize: (state) => ({
        theme: state.theme,
        sidebarCollapsed: state.sidebarCollapsed
      })
    }
  )
)
