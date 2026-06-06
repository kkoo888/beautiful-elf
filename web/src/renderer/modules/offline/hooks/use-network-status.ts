/** 网络状态 Hook */

import { useState, useEffect, useRef } from 'react'
import type { NetworkStatusType } from '../types/offline'

interface UseNetworkStatusReturn {
  isOnline: boolean
  wasOffline: boolean
  status: NetworkStatusType
}

/**
 * 网络状态监听 Hook
 * 监听 navigator.onLine + online/offline 事件
 * 网络恢复时短暂显示 syncing 状态后自动切回 online
 */
export function useNetworkStatus(onRecover?: () => void): UseNetworkStatusReturn {
  const [isOnline, setIsOnline] = useState(navigator.onLine)
  const [wasOffline, setWasOffline] = useState(false)
  const [status, setStatus] = useState<NetworkStatusType>(navigator.onLine ? 'online' : 'offline')
  const recoverRef = useRef(onRecover)
  recoverRef.current = onRecover

  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true)
      if (!navigator.onLine) return

      // 之前是离线状态 → 恢复中
      setWasOffline(true)
      setStatus('syncing')

      // 触发恢复回调
      recoverRef.current?.()

      // 3 秒后切回 online
      setTimeout(() => {
        setStatus('online')
        // 5 秒后清除 wasOffline
        setTimeout(() => setWasOffline(false), 2000)
      }, 3000)
    }

    const handleOffline = () => {
      setIsOnline(false)
      setStatus('offline')
    }

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)

    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [])

  return { isOnline, wasOffline, status }
}
