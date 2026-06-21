/**
 * 关于与更新组件
 * 版本信息 + 检查更新按钮
 */

import { useCallback, useState } from 'react'
import { Button, Typography, Space, Tag } from 'antd'
import { GithubOutlined, SyncOutlined, CheckCircleOutlined } from '@ant-design/icons'
import styles from './settings-panel.module.css'

const { Text, Link } = Typography

const APP_VERSION = '0.1.0'
const APP_NAME = 'Beautiful Elf'

export function AboutSettings() {
  const [checking, setChecking] = useState(false)
  const [updateStatus, setUpdateStatus] = useState<'idle' | 'latest' | 'available'>('idle')

  const handleCheckUpdate = useCallback(async () => {
    setChecking(true)
    setUpdateStatus('idle')
    // Mock: 延迟后提示已是最新
    await new Promise((r) => setTimeout(r, 1500))
    setUpdateStatus('latest')
    setChecking(false)
  }, [])

  return (
    <div className={styles.aboutCard}>
      <div className={styles.appIcon}>🧝</div>
      <Typography.Title level={4} style={{ marginBottom: 4 }}>
        {APP_NAME}
      </Typography.Title>
      <div className={styles.version}>
        <Tag>v{APP_VERSION}</Tag>
        <Tag color="blue">Electron</Tag>
        <Tag color="green">React 19</Tag>
      </div>
      <Text type="secondary" style={{ display: 'block', marginBottom: 20 }}>
        你的数字好朋友
      </Text>
      <Space>
        <Button
          type="primary"
          icon={<SyncOutlined spin={checking} />}
          loading={checking}
          onClick={handleCheckUpdate}
        >
          检查更新
        </Button>
        <Button
          icon={<GithubOutlined />}
          href="https://github.com/kkoo888/beautiful-elf"
          target="_blank"
        >
          GitHub
        </Button>
      </Space>
      {updateStatus === 'latest' && (
        <div style={{ marginTop: 12 }}>
          <Text type="success">
            <CheckCircleOutlined /> 已是最新版本
          </Text>
        </div>
      )}
    </div>
  )
}
