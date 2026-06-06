/** 天气模块类型定义 */

/** 天气状况 */
export type WeatherCondition = 'sunny' | 'cloudy' | 'rainy' | 'overcast' | 'snowy' | 'windy'

/** 天气预报 */
export interface Forecast {
  /** 日期 (YYYY-MM-DD) */
  date: string
  /** 最高温度 (°C) */
  tempHigh: number
  /** 最低温度 (°C) */
  tempLow: number
  /** 天气状况 */
  condition: WeatherCondition
  /** 天气图标 */
  icon: string
}

/** 天气数据 */
export interface WeatherData {
  /** 城市 */
  city: string
  /** 当前温度 (°C) */
  temperature: number
  /** 湿度 (%) */
  humidity: number
  /** 风速 (km/h) */
  windSpeed: number
  /** 天气状况 */
  condition: WeatherCondition
  /** 天气图标 */
  icon: string
  /** 未来几天预报 */
  forecast: Forecast[]
}

/** 天气状况映射 */
export const WEATHER_ICONS: Record<WeatherCondition, string> = {
  sunny: '☀️',
  cloudy: '⛅',
  rainy: '🌧️',
  overcast: '☁️',
  snowy: '❄️',
  windy: '🌬️',
}

/** 天气状况中文 */
export const WEATHER_LABELS: Record<WeatherCondition, string> = {
  sunny: '晴天',
  cloudy: '多云',
  rainy: '小雨',
  overcast: '阴天',
  snowy: '雪',
  windy: '大风',
}
