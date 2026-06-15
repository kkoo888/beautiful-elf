/**
 * 天气卡片组件
 * 使用 Ant Design Card 展示当前天气信息
 */

import React from 'react'
import { Card, Descriptions, Spin } from 'antd'
import type { WeatherData } from '../types/weather'
import { WEATHER_LABELS } from '../types/weather'

export interface WeatherCardProps {
  /** 天气数据 */
  data: WeatherData | undefined
  /** 是否加载中 */
  loading?: boolean
}

export const WeatherCard: React.FC<WeatherCardProps> = ({ data, loading }) => {
  if (loading || !data) {
    return (
      <Card style={{ textAlign: 'center', padding: '40px 0' }}>
        <Spin description="加载天气数据中..." />
      </Card>
    )
  }

  return (
    <Card
      title={
        <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 28 }}>{data.icon}</span>
          <span>{data.city}</span>
        </span>
      }
      style={{ borderRadius: 12 }}
    >
      <Descriptions column={2} size="small">
        <Descriptions.Item label="温度">
          <span style={{ fontSize: 20, fontWeight: 700 }}>{data.temperature}°C</span>
        </Descriptions.Item>
        <Descriptions.Item label="天气">
          {data.icon} {WEATHER_LABELS[data.condition]}
        </Descriptions.Item>
        <Descriptions.Item label="湿度">💧 {data.humidity}%</Descriptions.Item>
        <Descriptions.Item label="风速">🌬️ {data.windSpeed} km/h</Descriptions.Item>
      </Descriptions>
    </Card>
  )
}
