/** 快捷键管理 Hook */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useCallback } from 'react'
import { message } from 'antd'
import type { HotkeyConfig } from '../types/system'
import { detectConflict } from '../types/system'
import { fetchHotkeys, updateHotkey, resetHotkeys } from '../services/hotkey-api'

const QUERY_KEY = ['hotkeys']

export function useHotkeys() {
  const queryClient = useQueryClient()

  const { data: hotkeys = [], isLoading } = useQuery({
    queryKey: QUERY_KEY,
    queryFn: fetchHotkeys,
  })

  const updateMut = useMutation({
    mutationFn: ({ id, shortcut }: { id: string; shortcut: string }) => updateHotkey(id, shortcut),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: QUERY_KEY })
    },
  })

  const resetMut = useMutation({
    mutationFn: resetHotkeys,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: QUERY_KEY })
    },
  })

  /** 检查快捷键冲突（返回冲突的 HotkeyConfig） */
  const checkConflict = useCallback(
    (shortcut: string, excludeId?: string): HotkeyConfig | undefined => {
      return hotkeys.find((h) => h.shortcut === shortcut && h.id !== excludeId && h.enabled)
    },
    [hotkeys]
  )

  /** 检查快捷键冲突（基于 action key，返回冲突的 action 名） */
  const detectHotkeyConflict = useCallback(
    (hotkeyMap: Record<string, string>, key: string, excludeAction?: string): string | null => {
      return detectConflict(hotkeyMap, key, excludeAction)
    },
    []
  )

  const updateHotkeyShortcut = useCallback(
    (id: string, shortcut: string) => {
      // 先检查冲突
      const conflict = checkConflict(shortcut, id)
      if (conflict) {
        void message.error(`快捷键 ${shortcut} 已被「${conflict.name}」占用`)
        return Promise.reject(new Error('conflict'))
      }
      return updateMut.mutateAsync({ id, shortcut })
    },
    [updateMut, checkConflict]
  )

  const resetToDefault = useCallback(() => resetMut.mutateAsync(), [resetMut])

  return {
    hotkeys,
    isLoading,
    checkConflict,
    detectConflict: detectHotkeyConflict,
    updateHotkeyShortcut,
    resetToDefault,
    isMutating: updateMut.isPending || resetMut.isPending,
  }
}
