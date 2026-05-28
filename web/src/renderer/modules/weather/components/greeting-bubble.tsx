/**
 * 主动问候气泡组件
 * 根据当前时间和天气生成问候语
 */

import React, { useMemo } from 'react'
import { Alert } from 'antd'
import type { WeatherData } from '../types/weather'
import { WEATHER_LABELS } from '../types/weather'

export interface GreetingBubbleProps {
  /** 天气数据 */
  weather: WeatherData | undefined
}

/** 根据时段生成问候 */
function getTimeGreeting(hour: number): string {
  if (hour < 6) return '夜深了，注意休息 🌙'
  if (hour < 9) return '早上好！新的一天开始了 🌅'
  if (hour < 12) return '上午好！工作加油 ☀️'
  if (hour < 14) return '中午好！记得吃午饭 🍱'
  if (hour < 18) return '下午好！保持专注 💪'
  if (hour < 21) return '晚上好！辛苦了一天 🌆'
  return '夜晚好！注意早点休息 🌃'
}

/** 根据天气生成提醒 */
function getWeatherTip(condition: string): string {
  switch (condition) {
    case 'rainy':
      return '今天有雨，出门记得带伞 ☔'
    case 'sunny':
      return '阳光明媚，适合户外活动 😎'
    case 'cloudy':
      return '今天多云，温度适宜 😊'
    case 'overcast':
      return '天阴阴的，注意保暖 🧣'
    case 'snowy':
      return '下雪了，注意防滑保暖 ⛄'
    case 'windy':
      return '风大，注意防风 🧥'
    default:
      return '祝你今天心情愉快 😊'
  }
}

export const GreetingBubble: React.FC<GreetingBubbleProps> = ({ weather }) => {
  const greeting = useMemo(() => {
    const hour = new Date().getHours()
    const timeGreeting = getTimeGreeting(hour)

    if (!weather) return timeGreeting

    const weatherTip = getWeatherTip(weather.condition)
    const tempTip =
      weather.temperature >= 35
        ? '天热注意防暑 🥵'
        : weather.temperature <= 5
          ? '天冷注意保暖 🧤'
          : ''

    return [timeGreeting, weatherTip, tempTip].filter(Boolean).join('，')
  }, [weather])

  return (
    <Alert
      message={greeting}
      type="info"
      showIcon={false}
      banner
      style={{
        borderRadius: 10,
        fontSize: 14,
        background: 'linear-gradient(135deg, #e6f7ff, #f0f5ff)',
        border: '1px solid #91d5ff',
      }}
    />
  )
}
