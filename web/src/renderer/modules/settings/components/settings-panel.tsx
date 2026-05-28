/**
 * 设置主面板
 * 使用 Ant Design Tabs 分区展示各配置项
 */

import { useCallback } from 'react'
import { Tabs, Alert, Spin, Typography } from 'antd'
import {
  CloudServerOutlined,
  RobotOutlined,
  SettingOutlined,
  KeyOutlined,
  SafetyOutlined,
  InfoCircleOutlined,
  HeartOutlined,
  FileTextOutlined,
} from '@ant-design/icons'
import { PageHeader } from '@/components/page-header'
import { useSettings } from '../hooks/use-settings'
import { OllamaSettings } from './ollama-settings'
import { AiSettings } from './ai-settings'
import { AppSettingsPanel } from './app-settings'
import { ShortcutSettings } from './shortcut-settings'
import { PrivacySettings } from './privacy-settings'
import { AboutSettings } from './about-settings'
import { SoulSettings } from './soul-settings'
import { PromptManager } from './prompt-manager'
import styles from './settings-panel.module.css'

const TAB_ITEMS = [
  {
    key: 'ollama',
    label: 'Ollama',
    icon: <CloudServerOutlined />,
  },
  {
    key: 'ai',
    label: 'AI 参数',
    icon: <RobotOutlined />,
  },
  {
    key: 'app',
    label: '应用',
    icon: <SettingOutlined />,
  },
  {
    key: 'shortcut',
    label: '快捷键',
    icon: <KeyOutlined />,
  },
  {
    key: 'privacy',
    label: '隐私安全',
    icon: <SafetyOutlined />,
  },
  {
    key: 'about',
    label: '关于',
    icon: <InfoCircleOutlined />,
  },
  {
    key: 'soul',
    label: '灵魂',
    icon: <HeartOutlined />,
  },
  {
    key: 'prompt',
    label: 'Prompt 管理',
    icon: <FileTextOutlined />,
  },
]

/** 设置主面板 */
export default function SettingsPanel() {
  const {
    settings,
    soul,
    isLoading,
    updateSettings,
    updateSoul,
    testOllamaConnection,
    loadModels,
    models,
    restartHint,
    clearRestartHint,
  } = useSettings()

  const renderTabContent = useCallback(
    (key: string) => {
      switch (key) {
        case 'ollama':
          return (
            <OllamaSettings
              settings={settings.ollama}
              models={models}
              onChange={(p) => updateSettings({ ollama: p })}
              onTestConnection={testOllamaConnection}
              onLoadModels={loadModels}
            />
          )
        case 'ai':
          return <AiSettings settings={settings.ai} onChange={(p) => updateSettings({ ai: p })} />
        case 'app':
          return (
            <AppSettingsPanel
              settings={settings.app}
              onChange={(p) => updateSettings({ app: p })}
            />
          )
        case 'shortcut':
          return <ShortcutSettings />
        case 'privacy':
          return (
            <PrivacySettings
              settings={settings.privacy}
              onChange={(p) => updateSettings({ privacy: p })}
            />
          )
        case 'about':
          return <AboutSettings />
        case 'soul':
          return <SoulSettings soul={soul} onChange={updateSoul} />
        case 'prompt':
          return <PromptManager />
        default:
          return null
      }
    },
    [settings, soul, models, updateSettings, updateSoul, testOllamaConnection, loadModels]
  )

  if (isLoading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', paddingTop: 120 }}>
        <Spin size="large" />
      </div>
    )
  }

  return (
    <div className={styles.settingsPanel}>
      <PageHeader title="⚙️ 设置" description="全局配置与个性化" />

      {restartHint && (
        <Alert
          className={styles.restartAlert}
          message="需要重启"
          description={restartHint}
          type="warning"
          showIcon
          closable
          onClose={clearRestartHint}
        />
      )}

      <div className={styles.settingsContent}>
        <Tabs
          tabPosition="left"
          items={TAB_ITEMS.map((item) => ({
            ...item,
            label: (
              <span>
                {item.icon}
                <span style={{ marginLeft: 8 }}>{item.label}</span>
              </span>
            ),
            children: renderTabContent(item.key),
          }))}
        />
      </div>
    </div>
  )
}
