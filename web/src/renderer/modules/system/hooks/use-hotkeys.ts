/** 快捷键管理 Hook */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useCallback, useMemo } from 'react'
import type { HotkeyConfig } from '../types/system'
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

  /** 检查快捷键冲突 */
  const checkConflict = useCallback(
    (shortcut: string, excludeId?: string): HotkeyConfig | undefined => {
      return hotkeys.find((h) => h.shortcut === shortcut && h.id !== excludeId && h.enabled)
    },
    [hotkeys]
  )

  const updateHotkeyShortcut = useCallback(
    (id: string, shortcut: string) => updateMut.mutateAsync({ id, shortcut }),
    [updateMut]
  )

  const resetToDefault = useCallback(() => resetMut.mutateAsync(), [resetMut])

  return {
    hotkeys,
    isLoading,
    checkConflict,
    updateHotkeyShortcut,
    resetToDefault,
    isMutating: updateMut.isPending || resetMut.isPending,
  }
}
