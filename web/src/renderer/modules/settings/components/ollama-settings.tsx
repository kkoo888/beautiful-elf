/**
 * Ollama 配置组件
 * 服务地址、测试连接、模型选择
 */

import { useCallback, useState } from 'react'
import { Input, Button, Select, Space, Typography, Spin, Tag } from 'antd'
import { ThunderboltOutlined, ReloadOutlined } from '@ant-design/icons'
import type { AppSettings, OllamaModel, ConnectionTestResult } from '../types/settings'
import styles from './settings-panel.module.css'

const { Text } = Typography

interface OllamaSettingsProps {
  settings: AppSettings['ollama']
  models: OllamaModel[]
  onChange: (partial: Partial<AppSettings['ollama']>) => void
  onTestConnection: () => Promise<ConnectionTestResult>
  onLoadModels: () => Promise<OllamaModel[]>
}

/** 格式化模型大小 */
function formatSize(bytes: number): string {
  const gb = bytes / 1_000_000_000
  return gb >= 1 ? `${gb.toFixed(1)} GB` : `${(bytes / 1_000_000).toFixed(0)} MB`
}

export function OllamaSettings({
  settings,
  models,
  onChange,
  onTestConnection,
  onLoadModels
}: OllamaSettingsProps) {
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<ConnectionTestResult | null>(null)
  const [loadingModels, setLoadingModels] = useState(false)

  const handleTest = useCallback(async () => {
    setTesting(true)
    setTestResult(null)
    try {
      const result = await onTestConnection()
      setTestResult(result)
    } finally {
      setTesting(false)
    }
  }, [onTestConnection])

  const handleRefreshModels = useCallback(async () => {
    setLoadingModels(true)
    try {
      await onLoadModels()
    } finally {
      setLoadingModels(false)
    }
  }, [onLoadModels])

  return (
    <div>
      {/* 服务地址 */}
      <div className={styles.formItem}>
        <Text className={styles.formLabel}>服务地址</Text>
        <Space.Compact style={{ width: '100%' }}>
          <Input
            value={settings.baseUrl}
            onChange={(e) => onChange({ baseUrl: e.target.value })}
            placeholder="http://localhost:11434"
            style={{ maxWidth: 400 }}
          />
          <Button
            type="primary"
            icon={<ThunderboltOutlined />}
            loading={testing}
            onClick={handleTest}
          >
            测试连接
          </Button>
        </Space.Compact>
        {testResult && (
          <div className={styles.connectionStatus}>
            <span
              className={`${styles.connectionDot} ${
                testResult.success ? styles.success : styles.error
              }`}
            />
            <Text type={testResult.success ? 'success' : 'danger'}>
              {testResult.message}
              {testResult.latency && ` (${testResult.latency}ms)`}
            </Text>
          </div>
        )}
      </div>

      {/* 模型选择 */}
      <div className={styles.formItem}>
        <Text className={styles.formLabel}>模型列表</Text>
        <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
          <div style={{ flex: 1, maxWidth: 400 }}>
            <Select
              className={styles.modelSelect}
              value={settings.chatModel || undefined}
              onChange={(val) => onChange({ chatModel: val })}
              placeholder="选择对话模型"
              style={{ width: '100%', marginBottom: 8 }}
              options={models.map((m) => ({
                label: `${m.name} (${formatSize(m.size)})`,
                value: m.name
              }))}
            />
            <Select
              className={styles.modelSelect}
              value={settings.embedModel || undefined}
              onChange={(val) => onChange({ embedModel: val })}
              placeholder="选择向量嵌入模型"
              style={{ width: '100%', marginBottom: 8 }}
              options={models.map((m) => ({
                label: `${m.name} (${formatSize(m.size)})`,
                value: m.name
              }))}
            />
            <Select
              className={styles.modelSelect}
              value={settings.visionModel || undefined}
              onChange={(val) => onChange({ visionModel: val })}
              placeholder="选择视觉模型"
              style={{ width: '100%' }}
              options={models.map((m) => ({
                label: `${m.name} (${formatSize(m.size)})`,
                value: m.name
              }))}
            />
          </div>
          <Button
            icon={<ReloadOutlined />}
            loading={loadingModels}
            onClick={handleRefreshModels}
          >
            刷新
          </Button>
        </div>
        {models.length > 0 && (
          <Text type="secondary" style={{ fontSize: 12, marginTop: 4, display: 'block' }}>
            已发现 {models.length} 个模型
          </Text>
        )}
      </div>
    </div>
  )
}
