/**
 * 隐私安全设置组件
 * 加密开关、日志级别、匿名统计
 */

import { Select, Switch, Typography, Space, Alert } from 'antd'
import type { AppSettings } from '../types/settings'
import styles from './settings-panel.module.css'

const { Text } = Typography

interface PrivacySettingsProps {
  settings: AppSettings['privacy']
  onChange: (partial: Partial<AppSettings['privacy']>) => void
}

const LOG_LEVEL_OPTIONS = [
  { label: 'Debug（调试）', value: 'debug' },
  { label: 'Info（信息）', value: 'info' },
  { label: 'Warn（警告）', value: 'warn' },
  { label: 'Error（错误）', value: 'error' },
]

export function PrivacySettings({ settings, onChange }: PrivacySettingsProps) {
  return (
    <div>
      <Alert
        message="所有数据均存储在本地，不会上传到云端。"
        type="info"
        showIcon
        style={{ marginBottom: 20 }}
      />

      {/* 数据加密 */}
      <div className={styles.formItem}>
        <Space>
          <Switch
            checked={settings.encryptData}
            onChange={(checked) => onChange({ encryptData: checked })}
          />
          <Text>启用数据加密</Text>
        </Space>
        <Text type="secondary" style={{ fontSize: 12, display: 'block', marginTop: 4 }}>
          对本地存储的对话和配置数据进行加密保护
        </Text>
      </div>

      {/* 日志级别 */}
      <div className={styles.formItem}>
        <Text className={styles.formLabel}>日志级别</Text>
        <Select
          value={settings.logLevel}
          onChange={(val) => onChange({ logLevel: val })}
          options={LOG_LEVEL_OPTIONS}
          style={{ width: 200 }}
        />
        <Text type="secondary" style={{ fontSize: 12, display: 'block', marginTop: 4 }}>
          Debug 模式会记录更多运行信息，可能影响性能
        </Text>
      </div>

      {/* 匿名统计 */}
      <div className={styles.formItem}>
        <Space>
          <Switch
            checked={settings.anonymousStats}
            onChange={(checked) => onChange({ anonymousStats: checked })}
          />
          <Text>允许匿名使用统计</Text>
        </Space>
        <Text type="secondary" style={{ fontSize: 12, display: 'block', marginTop: 4 }}>
          帮助我们改进产品，不收集任何个人数据
        </Text>
      </div>
    </div>
  )
}
