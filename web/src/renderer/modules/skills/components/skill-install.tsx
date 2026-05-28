/** 安装技能组件（Drawer） */

import { useState, useCallback } from 'react'
import { Drawer, Upload, Input, Button, Typography, Divider, message } from 'antd'
import { UploadOutlined, GithubOutlined, InboxOutlined } from '@ant-design/icons'
import type { UploadProps } from 'antd'
import type { InstallSkillInput } from '../types/skills'
import styles from './skills-panel.module.css'

const { Dragger } = Upload
const { Text } = Typography

interface SkillInstallProps {
  open: boolean
  onClose: () => void
  onInstall: (input: InstallSkillInput) => Promise<void>
  isLoading?: boolean
}

/** 安装技能 Drawer */
export function SkillInstall({ open, onClose, onInstall, isLoading }: SkillInstallProps) {
  const [githubUrl, setGithubUrl] = useState('')

  const handleFileUpload: UploadProps['customRequest'] = useCallback(
    async (options) => {
      const file = options.file as File
      const reader = new FileReader()
      reader.onload = async () => {
        const base64 = (reader.result as string).split(',')[1] ?? ''
        try {
          await onInstall({ source: 'file', content: base64 })
          message.success(`已安装技能: ${file.name}`)
          onClose()
        } catch {
          message.error('安装失败，请重试')
        }
      }
      reader.readAsDataURL(file)
    },
    [onInstall, onClose]
  )

  const handleGithubImport = useCallback(async () => {
    if (!githubUrl.trim()) {
      message.warning('请输入 GitHub 仓库地址')
      return
    }
    try {
      await onInstall({ source: 'github', content: githubUrl.trim() })
      message.success('已从 GitHub 导入技能')
      setGithubUrl('')
      onClose()
    } catch {
      message.error('导入失败，请检查仓库地址')
    }
  }, [githubUrl, onInstall, onClose])

  return (
    <Drawer title="📦 安装技能" open={open} onClose={onClose} width={400} destroyOnClose>
      <div className={styles.installContent}>
        {/* 文件上传 */}
        <div className={styles.installSection}>
          <h4 className={styles.sectionTitle}>从文件安装</h4>
          <Dragger
            accept=".skill,.zip,.tar.gz"
            showUploadList={false}
            customRequest={handleFileUpload}
            disabled={isLoading}
          >
            <div className={styles.uploadArea}>
              <p className="ant-upload-drag-icon">
                <InboxOutlined />
              </p>
              <p className="ant-upload-text">点击或拖拽 .skill 文件到此区域</p>
              <p className="ant-upload-hint">支持 .skill、.zip、.tar.gz 格式</p>
            </div>
          </Dragger>
        </div>

        <Divider plain>或</Divider>

        {/* GitHub 导入 */}
        <div className={styles.installSection}>
          <h4 className={styles.sectionTitle}>
            <GithubOutlined /> 从 GitHub 导入
          </h4>
          <div className={styles.githubInput}>
            <Input
              placeholder="user/repo 或完整 URL"
              value={githubUrl}
              onChange={(e) => setGithubUrl(e.target.value)}
              onPressEnter={() => void handleGithubImport()}
              disabled={isLoading}
            />
            <Button type="primary" onClick={() => void handleGithubImport()} loading={isLoading}>
              导入
            </Button>
          </div>
          <Text type="secondary" style={{ fontSize: 12 }}>
            输入 GitHub 仓库地址，格式：user/repo 或 https://github.com/user/repo
          </Text>
        </div>
      </div>
    </Drawer>
  )
}
