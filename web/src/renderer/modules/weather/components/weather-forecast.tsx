/**
 * 未来 3 天预报组件
 * 使用 Ant Design List 展示每日预报
 */

import React from 'react'
import { List, Card } from 'antd'
import type { Forecast } from '../types/weather'
import { WEATHER_LABELS } from '../types/weather'

export interface WeatherForecastProps {
  /** 预报数据列表 */
  forecast: Forecast[]
}

/** 格式化日期为中文 */
function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  const weekdays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
  const month = date.getMonth() + 1
  const day = date.getDate()
  const weekday = weekdays[date.getDay()]
  return `${month}月${day}日 ${weekday}`
}

export const WeatherForecast: React.FC<WeatherForecastProps> = ({ forecast }) => {
  return (
    <List
      grid={{ gutter: 12, column: 3 }}
      dataSource={forecast}
      renderItem={(item) => (
        <List.Item>
          <Card
            size="small"
            style={{ textAlign: 'center', borderRadius: 10 }}
            styles={{ body: { padding: '12px 8px' } }}
          >
            <div
              style={{ fontSize: 12, color: 'var(--ant-color-text-secondary)', marginBottom: 4 }}
            >
              {formatDate(item.date)}
            </div>
            <div style={{ fontSize: 28, marginBottom: 4 }}>{item.icon}</div>
            <div style={{ fontSize: 12, marginBottom: 4 }}>{WEATHER_LABELS[item.condition]}</div>
            <div style={{ fontSize: 13, fontWeight: 600 }}>
              <span style={{ color: 'var(--ant-color-error)' }}>{item.tempHigh}°</span>
              {' / '}
              <span style={{ color: 'var(--ant-color-primary)' }}>{item.tempLow}°</span>
            </div>
          </Card>
        </List.Item>
      )}
    />
  )
}
