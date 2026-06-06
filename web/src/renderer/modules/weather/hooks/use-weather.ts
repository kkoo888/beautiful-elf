/** 天气状态管理 hook（TanStack Query） */

import { useQuery } from '@tanstack/react-query'
import type { WeatherData } from '../types/weather'
import { fetchWeather } from '../services/weather-api'

const WEATHER_KEY = (city: string) => ['weather', city]

export interface UseWeatherReturn {
  /** 天气数据 */
  data: WeatherData | undefined
  /** 是否加载中 */
  isLoading: boolean
  /** 错误信息 */
  error: Error | null
  /** 手动刷新 */
  refetch: () => void
}

/**
 * 天气数据 hook
 * @param city 城市名称，默认北京
 * @param staleTime 缓存时间（毫秒），默认 30 分钟
 */
export function useWeather(city = '北京', staleTime = 30 * 60 * 1000): UseWeatherReturn {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: WEATHER_KEY(city),
    queryFn: () => fetchWeather(city),
    staleTime,
    refetchOnWindowFocus: false,
  })

  return {
    data,
    isLoading,
    error: error as Error | null,
    refetch: () => void refetch(),
  }
}
