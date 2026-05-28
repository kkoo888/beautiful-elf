/**
 * 应用设置组件
 * 语言、开机自启、启动行为、关闭行为
 */

import { useCallback } from 'react'
import { Select, Switch, Typography, Radio, Space } from 'antd'
import type { AppSettings } from '../types/settings'
import styles from './settings-panel.module.css'

const { Text } = Typography

interface AppSettingsProps {
  settings: AppSettings['app']
  onChange: (partial: Partial<AppSettings['app']>) => void
}

const LANGUAGE_OPTIONS = [
  { label: '简体中文', value: 'zh-CN' },
  { label: 'English', value: 'en-US' },
  { label: '日本語', value: 'ja-JP' }
]

export function AppSettingsPanel({ settings, onChange }: AppSettingsProps) {
  const handleLanguage = useCallback(
    (val: string) => onChange({ language: val }),
    [onChange]
  )

  return (
    <div>
      {/* 语言 */}
      <div className={styles.formItem}>
        <Text className={styles.formLabel}>语言</Text>
        <Select
          value={settings.language}
          onChange={handleLanguage}
          options={LANGUAGE_OPTIONS}
          style={{ width: 200 }}
        />
      </div>

      {/* 开机自启 */}
      <div className={styles.formItem}>
        <Space>
          <Switch
            checked={settings.autoLaunch}
            onChange={(checked) => onChange({ autoLaunch: checked })}
          />
          <Text>开机自动启动</Text>
        </Space>
      </div>

      {/* 最小化到托盘 */}
      <div className={styles.formItem}>
        <Space>
          <Switch
            checked={settings.minimizeToTray}
            onChange={(checked) => onChange({ minimizeToTray: checked })}
          />
          <Text>关闭窗口时最小化到系统托盘</Text>
        </Space>
      </div>

      {/* 关闭行为 */}
      <div className={styles.formItem}>
        <Text className={styles.formLabel}>关闭行为</Text>
        <Radio.Group
          value={settings.closeBehavior}
          onChange={(e) => onChange({ closeBehavior: e.target.value })}
        >
          <Space direction="vertical">
            <Radio value="minimize">最小化到托盘</Radio>
            <Radio value="exit">直接退出</Radio>
          </Space>
        </Radio.Group>
      </div>
    </div>
  )
}
