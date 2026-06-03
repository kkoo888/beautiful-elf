/** 安装技能组件（Drawer）— 文件夹选择 + 元数据编辑 */

import { useState, useCallback, useRef } from 'react'
import {
  Drawer,
  Input,
  Button,
  Typography,
  Divider,
  Tag,
  message,
  Steps,
  Space,
  FolderOpenOutlined,
  GithubOutlined,
  FileOutlined,
} from 'antd'
import type { InstallSkillInput, SkillFolderParsed } from '../types/skills'
import { parseSkillFolder } from '../utils/skill-folder-parser'
import styles from './skills-panel.module.css'

const { Text } = Typography

interface SkillInstallProps {
  open: boolean
  onClose: () => void
  onInstall: (input: InstallSkillInput) => Promise<void>
  isLoading?: boolean
}

/** 安装步骤 */
type InstallStep = 'source' | 'edit'

/** 安装技能 Drawer */
export function SkillInstall({ open, onClose, onInstall, isLoading }: SkillInstallProps) {
  // ─── 步骤控制 ──────────────────────────────
  const [step, setStep] = useState<InstallStep>('source')

  // ─── 文件夹选择 ──────────────────────────────
  const folderInputRef = useRef<HTMLInputElement>(null)
  const [parsed, setParsed] = useState<SkillFolderParsed | null>(null)

  // ─── GitHub 导入 ──────────────────────────────
  const [githubUrl, setGithubUrl] = useState('')

  // ─── 编辑表单 ──────────────────────────────
  const [formName, setFormName] = useState('')
  const [formDisplayName, setFormDisplayName] = useState('')
  const [formDescription, setFormDescription] = useState('')
  const [formVersion, setFormVersion] = useState('1.0.0')
  const [formTriggerWords, setFormTriggerWords] = useState('')
  const [formDependencies, setFormDependencies] = useState('')

  // ─── 重置状态 ──────────────────────────────
  const resetState = useCallback(() => {
    setStep('source')
    setParsed(null)
    setGithubUrl('')
    setFormName('')
    setFormDisplayName('')
    setFormDescription('')
    setFormVersion('1.0.0')
    setFormTriggerWords('')
    setFormDependencies('')
  }, [])

  const handleClose = useCallback(() => {
    resetState()
    onClose()
  }, [resetState, onClose])

  // ─── 文件夹选择处理 ──────────────────────────────
  const handleFolderSelect = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const fileList = e.target.files
      if (!fileList || fileList.length === 0) return

      try {
        const result = await parseSkillFolder(fileList)
        setParsed(result)

        // 自动填充表单
        setFormName(result.folderName)
        setFormDisplayName(result.extractedName ?? result.folderName)
        setFormDescription(result.extractedDescription ?? '')
        setFormVersion(result.extractedVersion ?? '1.0.0')
        setFormTriggerWords(result.extractedTriggerWords?.join(', ') ?? '')
        setFormDependencies(result.extractedDependencies?.join(', ') ?? '')

        setStep('edit')
      } catch {
        message.error('解析文件夹失败，请检查内容')
      }

      // 清空 input 以便重复选择同一文件夹
      e.target.value = ''
    },
    []
  )

  // ─── GitHub 导入处理 ──────────────────────────────
  const handleGithubImport = useCallback(() => {
    if (!githubUrl.trim()) {
      message.warning('请输入 GitHub 仓库地址')
      return
    }
    const repoName = githubUrl.trim().split('/').pop()?.replace('.git', '') || 'imported-skill'
    setFormName(repoName)
    setFormDisplayName(repoName)
    setFormDescription(`从 GitHub 导入: ${githubUrl.trim()}`)
    setFormVersion('1.0.0')
    setFormTriggerWords('')
    setFormDependencies('')
    setParsed(null)
    setStep('edit')
  }, [githubUrl])

  // ─── 确认安装 ──────────────────────────────
  const handleConfirm = useCallback(async () => {
    if (!formName.trim()) {
      message.warning('请输入技能名称')
      return
    }
    if (!formDescription.trim()) {
      message.warning('请输入技能简介')
      return
    }

    const triggerWords = formTriggerWords
      .split(/[,，]/)
      .map((w) => w.trim())
      .filter(Boolean)
    const dependencies = formDependencies
      .split(/[,，]/)
      .map((d) => d.trim())
      .filter(Boolean)

    try {
      await onInstall({
        source: parsed ? 'folder' : 'github',
        name: formName.trim(),
        displayName: formDisplayName.trim() || formName.trim(),
        description: formDescription.trim(),
        version: formVersion.trim() || '1.0.0',
        triggerWords,
        dependencies,
        content: parsed
          ? btoa(unescape(encodeURIComponent(JSON.stringify(parsed.files))))
          : githubUrl.trim(),
      })
      message.success(`已安装技能: ${formName.trim()}`)
      handleClose()
    } catch {
      message.error('安装失败，请重试')
    }
  }, [
    formName,
    formDisplayName,
    formDescription,
    formVersion,
    formTriggerWords,
    formDependencies,
    parsed,
    githubUrl,
    onInstall,
    handleClose,
  ])

  // ─── 渲染 ──────────────────────────────
  return (
    <Drawer
      title="📦 安装技能"
      open={open}
      onClose={handleClose}
      width={440}
      destroyOnClose
      footer={
        step === 'edit' ? (
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <Button onClick={() => setStep('source')}>上一步</Button>
            <Space>
              <Button onClick={handleClose}>取消</Button>
              <Button type="primary" onClick={() => void handleConfirm()} loading={isLoading}>
                确认安装
              </Button>
            </Space>
          </div>
        ) : undefined
      }
    >
      <Steps
        current={step === 'source' ? 0 : 1}
        size="small"
        items={[{ title: '选择来源' }, { title: '编辑信息' }]}
        style={{ marginBottom: 24 }}
      />

      {step === 'source' && (
        <div className={styles.installContent}>
          {/* 文件夹选择 */}
          <div className={styles.installSection}>
            <h4 className={styles.sectionTitle}>
              <FolderOpenOutlined /> 从文件夹安装
            </h4>
            <input
              ref={folderInputRef}
              type="file"
              // @ts-expect-error webkitdirectory 非标准属性
              webkitdirectory=""
              mozdirectory=""
              directory=""
              style={{ display: 'none' }}
              onChange={handleFolderSelect}
            />
            <div
              className={styles.folderDropzone}
              onClick={() => folderInputRef.current?.click()}
              onDragOver={(e) => {
                e.preventDefault()
                e.stopPropagation()
              }}
              onDrop={(e) => {
                e.preventDefault()
                e.stopPropagation()
                // 拖拽文件夹需要通过 input 触发，这里引导用户点击
                folderInputRef.current?.click()
              }}
            >
              <p style={{ fontSize: 32, margin: 0 }}>📂</p>
              <p style={{ margin: '8px 0 4px', fontWeight: 500 }}>点击选择技能文件夹</p>
              <Text type="secondary" style={{ fontSize: 12 }}>
                文件夹名将作为技能名称，文件夹内需包含 SKILL.md
              </Text>
            </div>
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
              <Button type="primary" onClick={() => void handleGithubImport()} disabled={isLoading}>
                下一步
              </Button>
            </div>
            <Text type="secondary" style={{ fontSize: 12 }}>
              输入 GitHub 仓库地址，格式：user/repo 或 https://github.com/user/repo
            </Text>
          </div>
        </div>
      )}

      {step === 'edit' && (
        <div className={styles.installContent}>
          {/* 来源信息 */}
          {parsed && (
            <div className={styles.folderPreview}>
              <FileOutlined style={{ marginRight: 8 }} />
              <Text strong>{parsed.folderName}/</Text>
              <Text type="secondary" style={{ marginLeft: 8, fontSize: 12 }}>
                {parsed.files.length} 个文件
              </Text>
            </div>
          )}

          {/* 技能名称 */}
          <div className={styles.installSection}>
            <label className={styles.formLabel}>
              技能名称 <span className={styles.required}>*</span>
            </label>
            <Input
              value={formName}
              onChange={(e) => setFormName(e.target.value)}
              placeholder="技能的唯一标识，如: my-awesome-skill"
              disabled={isLoading}
            />
            <Text type="secondary" style={{ fontSize: 11 }}>
              英文、数字、连字符，文件夹名即默认值
            </Text>
          </div>

          {/* 显示名称 */}
          <div className={styles.installSection}>
            <label className={styles.formLabel}>显示名称</label>
            <Input
              value={formDisplayName}
              onChange={(e) => setFormDisplayName(e.target.value)}
              placeholder="用于界面展示的友好名称"
              disabled={isLoading}
            />
          </div>

          {/* 技能简介 */}
          <div className={styles.installSection}>
            <label className={styles.formLabel}>
              技能简介 <span className={styles.required}>*</span>
            </label>
            <Input.TextArea
              value={formDescription}
              onChange={(e) => setFormDescription(e.target.value)}
              placeholder="描述这个技能的用途和功能"
              autoSize={{ minRows: 2, maxRows: 4 }}
              disabled={isLoading}
              showCount
              maxLength={1024}
            />
          </div>

          {/* 版本号 */}
          <div className={styles.installSection}>
            <label className={styles.formLabel}>版本号</label>
            <Input
              value={formVersion}
              onChange={(e) => setFormVersion(e.target.value)}
              placeholder="1.0.0"
              disabled={isLoading}
              style={{ width: 120 }}
            />
          </div>

          {/* 触发词 */}
          <div className={styles.installSection}>
            <label className={styles.formLabel}>触发词</label>
            <Input
              value={formTriggerWords}
              onChange={(e) => setFormTriggerWords(e.target.value)}
              placeholder="用逗号分隔，如: debug, 排查, 诊断"
              disabled={isLoading}
            />
            {formTriggerWords && (
              <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginTop: 4 }}>
                {formTriggerWords.split(/[,，]/).map((w) => w.trim()).filter(Boolean).map((word) => (
                  <Tag key={word} color="orange" style={{ fontSize: 11 }}>
                    {word}
                  </Tag>
                ))}
              </div>
            )}
          </div>

          {/* 依赖技能 */}
          <div className={styles.installSection}>
            <label className={styles.formLabel}>依赖技能</label>
            <Input
              value={formDependencies}
              onChange={(e) => setFormDependencies(e.target.value)}
              placeholder="用逗号分隔，如: tdd, writing-plans"
              disabled={isLoading}
            />
            {formDependencies && (
              <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginTop: 4 }}>
                {formDependencies.split(/[,，]/).map((d) => d.trim()).filter(Boolean).map((dep) => (
                  <Tag key={dep} style={{ fontSize: 11 }}>
                    {dep}
                  </Tag>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </Drawer>
  )
}
