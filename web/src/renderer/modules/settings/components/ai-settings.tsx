/**
 * AI 设置组件
 * 温度、最大 Token、Top-P、系统提示词
 */

import { useCallback } from 'react'
import { Slider, InputNumber, Typography } from 'antd'
import type { AppSettings } from '../types/settings'
import styles from './settings-panel.module.css'

const { Text } = Typography
const { TextArea } = Input

interface AiSettingsProps {
  settings: AppSettings['ai']
  onChange: (partial: Partial<AppSettings['ai']>) => void
}

/** 滑块 + 数值输入行 */
function SliderRow({
  label,
  value,
  min,
  max,
  step,
  onChange,
}: {
  label: string
  value: number
  min: number
  max: number
  step: number
  onChange: (val: number | null) => void
}) {
  return (
    <div className={styles.formItem}>
      <Text className={styles.formLabel}>{label}</Text>
      <div className={styles.sliderRow}>
        <Slider
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={onChange}
          style={{ flex: 1 }}
          tooltip={{ formatter: (v) => `${v}` }}
        />
        <InputNumber
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={onChange}
          style={{ width: 80 }}
        />
      </div>
    </div>
  )
}

export function AiSettings({ settings, onChange }: AiSettingsProps) {
  const handleTemperature = useCallback(
    (val: number | null) => {
      if (val !== null) onChange({ temperature: val })
    },
    [onChange]
  )

  const handleMaxTokens = useCallback(
    (val: number | null) => {
      if (val !== null) onChange({ maxTokens: val })
    },
    [onChange]
  )

  const handleTopP = useCallback(
    (val: number | null) => {
      if (val !== null) onChange({ topP: val })
    },
    [onChange]
  )

  return (
    <div>
      <SliderRow
        label="温度 (Temperature)"
        value={settings.temperature}
        min={0}
        max={2}
        step={0.1}
        onChange={handleTemperature}
      />

      <SliderRow
        label="最大 Token (Max Tokens)"
        value={settings.maxTokens}
        min={1}
        max={8192}
        step={64}
        onChange={handleMaxTokens}
      />

      <SliderRow
        label="Top-P"
        value={settings.topP}
        min={0}
        max={1}
        step={0.05}
        onChange={handleTopP}
      />

      <div className={styles.formItem}>
        <Text className={styles.formLabel}>系统提示词</Text>
        <TextArea
          className={styles.systemPrompt}
          value={settings.systemPrompt}
          onChange={(e) => onChange({ systemPrompt: e.target.value })}
          placeholder="设置 AI 的行为和人设..."
          rows={4}
          maxLength={2000}
          showCount
        />
      </div>
    </div>
  )
}
