/** 天气 API 服务（mock 实现） */

import type { WeatherData, WeatherCondition, Forecast } from '../types/weather'
import { WEATHER_ICONS } from '../types/weather'

/** 城市 mock 数据库 */
const CITY_WEATHER: Record<string, Omit<WeatherData, 'forecast'>> = {
  北京: {
    city: '北京',
    temperature: 28,
    humidity: 45,
    windSpeed: 12,
    condition: 'sunny',
    icon: WEATHER_ICONS.sunny,
  },
  上海: {
    city: '上海',
    temperature: 26,
    humidity: 72,
    windSpeed: 8,
    condition: 'cloudy',
    icon: WEATHER_ICONS.cloudy,
  },
  广州: {
    city: '广州',
    temperature: 32,
    humidity: 85,
    windSpeed: 6,
    condition: 'rainy',
    icon: WEATHER_ICONS.rainy,
  },
  深圳: {
    city: '深圳',
    temperature: 31,
    humidity: 80,
    windSpeed: 10,
    condition: 'cloudy',
    icon: WEATHER_ICONS.cloudy,
  },
  杭州: {
    city: '杭州',
    temperature: 25,
    humidity: 68,
    windSpeed: 7,
    condition: 'overcast',
    icon: WEATHER_ICONS.overcast,
  },
  成都: {
    city: '成都',
    temperature: 24,
    humidity: 60,
    windSpeed: 5,
    condition: 'cloudy',
    icon: WEATHER_ICONS.cloudy,
  },
}

/** 生成随机波动 */
function jitter(value: number, range: number): number {
  return Math.round(value + (Math.random() - 0.5) * range)
}

/** 生成未来几天预报 */
function generateForecast(baseTemp: number, baseCondition: WeatherCondition): Forecast[] {
  const conditions: WeatherCondition[] = ['sunny', 'cloudy', 'rainy', 'overcast']
  const today = new Date()

  return Array.from({ length: 3 }, (_, i) => {
    const date = new Date(today)
    date.setDate(date.getDate() + i + 1)

    // 随机微调天气
    const condition =
      i === 0 ? baseCondition : conditions[Math.floor(Math.random() * conditions.length)]

    return {
      date: date.toISOString().split('T')[0],
      tempHigh: jitter(baseTemp + 3, 4),
      tempLow: jitter(baseTemp - 5, 4),
      condition,
      icon: WEATHER_ICONS[condition],
    }
  })
}

/**
 * 获取天气数据
 * @param city 城市名称，默认北京
 */
export async function fetchWeather(city = '北京'): Promise<WeatherData> {
  // 模拟网络延迟
  await new Promise((r) => setTimeout(r, 300))

  // 尝试精确匹配，否则使用北京 + 随机波动
  const base = CITY_WEATHER[city] ?? {
    ...CITY_WEATHER['北京'],
    city,
    temperature: jitter(22, 10),
    humidity: jitter(55, 30),
  }

  // 加一点随机波动，模拟实时变化
  const weather: WeatherData = {
    ...base,
    temperature: jitter(base.temperature, 3),
    humidity: Math.max(20, Math.min(100, jitter(base.humidity, 5))),
    windSpeed: Math.max(0, jitter(base.windSpeed, 4)),
    forecast: generateForecast(base.temperature, base.condition),
  }

  return weather
}
