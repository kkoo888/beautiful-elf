/**
 * 天气主面板
 * 展示当前天气 + 3天预报 + 问候气泡
 */

import React from 'react'
import { Spin } from 'antd'
import { PageHeader } from '@/components/page-header'
import { useWeather } from './hooks/use-weather'
import { WeatherCard } from './weather-card'
import { WeatherForecast } from './weather-forecast'
import { GreetingBubble } from './greeting-bubble'
import styles from './weather-panel.module.css'

/** 天气主面板 */
export default function WeatherPanel() {
  const { data, isLoading } = useWeather()

  return (
    <div className={styles.panel}>
      <PageHeader title="🌤️ 天气助手" description="天气信息 & 智能问候" />

      {/* 问候气泡 */}
      <GreetingBubble weather={data} />

      {isLoading ? (
        <div style={{ textAlign: 'center', padding: '60px 0' }}>
          <Spin size="large" tip="加载天气数据中..." />
        </div>
      ) : (
        <div className={styles.weatherMain}>
          {/* 当前天气卡片 */}
          <WeatherCard data={data} loading={isLoading} />

          {/* 3 天预报 */}
          {data && (
            <div className={styles.forecastSection}>
              <h4 style={{ marginBottom: 12, color: 'var(--ant-color-text)' }}>📅 未来 3 天预报</h4>
              <WeatherForecast forecast={data.forecast} />
            </div>
          )}
        </div>
      )}
    </div>
  )
}
