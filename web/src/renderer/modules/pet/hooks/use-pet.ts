import { useState, useEffect, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useElectronApi } from '@/hooks'
import { fetchPetAttributes, interact, fetchInteractions } from '../services/pet-api'
import type { PetInteractionType, Live2DModelInfo, PetRuntimeStatus } from '../types/pet'

/** 默认模型信息 */
const DEFAULT_MODEL_INFO: Live2DModelInfo = {
  name: '',
  version: '',
  engine: 'Live2 Cubism 5',
  expressionCount: 0,
  motionCount: 0,
  ready: false,
}

/** 默认运行状态 */
const DEFAULT_RUNTIME_STATUS: PetRuntimeStatus = {
  libraryLoaded: false,
  mouseFollow: true,
  clickInteraction: false,
  lipSync: false,
  currentExpression: '默认',
  currentMotion: '默认',
  bubbleText: '',
  motionQueueCount: 0,
  fps: 0,
}

export function usePet() {
  const queryClient = useQueryClient()
  const { pet: petApi, isElectron } = useElectronApi()

  // 窗口可见性
  const [windowVisible, setWindowVisible] = useState(false)
  const [screenshot, setScreenshot] = useState<string | null>(null)

  // Live2D 模型信息 & 运行状态（从宠物窗口获取）
  const [modelInfo, setModelInfo] = useState<Live2DModelInfo>(DEFAULT_MODEL_INFO)
  const [runtimeStatus, setRuntimeStatus] = useState<PetRuntimeStatus>(DEFAULT_RUNTIME_STATUS)

  // 监听宠物窗口事件
  useEffect(() => {
    if (!isElectron) return

    const cleanupScreenshot = petApi.onScreenshotUpdate((data: string) => {
      setScreenshot(data)
    })

    const cleanupVisibility = petApi.onVisibilityChange((visible: boolean) => {
      setWindowVisible(visible)
      if (!visible) {
        // 窗口关闭时重置状态
        setModelInfo(DEFAULT_MODEL_INFO)
        setRuntimeStatus(DEFAULT_RUNTIME_STATUS)
      }
    })

    return () => {
      cleanupScreenshot()
      cleanupVisibility()
    }
  }, [isElectron, petApi])

  // 切换宠物窗口
  const toggleWindow = useCallback(async () => {
    if (!isElectron) return
    await petApi.toggle()
  }, [isElectron, petApi])

  // 刷新模型信息（从宠物窗口获取属性）
  const refreshModelInfo = useCallback(async () => {
    if (!isElectron || !windowVisible) return
    try {
      const attrs = await petApi.getAttributes()
      if (attrs && 'error' in attrs) return
      // 如果宠物窗口返回了属性数据，更新状态
      if (attrs && 'name' in attrs) {
        setModelInfo((prev) => ({
          ...prev,
          name: (attrs as any).name ?? prev.name,
          ready: true,
        }))
      }
    } catch {
      // 静默处理
    }
  }, [isElectron, windowVisible, petApi])

  // 轮询刷新（窗口可见时）
  useEffect(() => {
    if (!windowVisible) return
    refreshModelInfo()
    const timer = setInterval(refreshModelInfo, 5000)
    return () => clearInterval(timer)
  }, [windowVisible, refreshModelInfo])

  // 切换鼠标跟随
  const toggleMouseFollow = useCallback(() => {
    setRuntimeStatus((prev) => ({ ...prev, mouseFollow: !prev.mouseFollow }))
    // TODO: 通知宠物窗口切换鼠标跟随
  }, [])

  // 切换帧率
  const setFps = useCallback((fps: number) => {
    setRuntimeStatus((prev) => ({ ...prev, fps }))
    // TODO: 通知宠物窗口切换帧率
  }, [])

  // 播放表情
  const playExpression = useCallback((name?: string) => {
    // TODO: 通知宠物窗口播放表情
    if (name) {
      setRuntimeStatus((prev) => ({ ...prev, currentExpression: name }))
    }
  }, [])

  // 播放动作
  const playMotion = useCallback((name?: string) => {
    // TODO: 通知宠物窗口播放动作
    if (name) {
      setRuntimeStatus((prev) => ({ ...prev, currentMotion: name }))
    }
  }, [])

  // 后端宠物属性查询
  const { data: attributes, isLoading } = useQuery({
    queryKey: ['pets'],
    queryFn: fetchPetAttributes,
    refetchInterval: 30000,
  })

  const { data: interactions = [] } = useQuery({
    queryKey: ['pet-interactions'],
    queryFn: fetchInteractions,
  })

  const mutation = useMutation({
    mutationFn: (type: PetInteractionType) => interact(type),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pets'] })
      queryClient.invalidateQueries({ queryKey: ['pet-interactions'] })
    },
  })

  return {
    // 后端宠物属性
    attributes: attributes ?? { hunger: 0, clean: 0, mood: 0, health: 0, intimacy: 0, level: 0 },
    isLoading,
    interact: mutation.mutateAsync,
    interactions,
    // 窗口状态
    windowVisible,
    screenshot,
    toggleWindow,
    // Live2D 模型
    modelInfo,
    runtimeStatus,
    refreshModelInfo,
    toggleMouseFollow,
    setFps,
    playExpression,
    playMotion,
  }
}
