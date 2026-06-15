/** 安装技能组件（Drawer）— 三步式：选择来源 → 安全扫描 → 编辑确认 */

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
  Alert,
  Spin,
} from 'antd'
import {
  FolderOpenOutlined,
  GithubOutlined,
  FileOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  CloseCircleOutlined,
  InfoCircleOutlined,
  LoadingOutlined,
} from '@ant-design/icons'
import JSZip from 'jszip'
import type { InstallSkillInput, SkillFolderParsed, ScanResult, RiskLevel } from '../types/skills'
import { parseSkillFolder, checkGitHubRepo } from '../utils/skill-folder-parser'
import { installSkillZip, confirmInstallZip, cleanupSkillDir } from '../services/skills-api'
import styles from './skills-panel.module.css'

const { Text } = Typography

interface SkillInstallProps {
  open: boolean
  onClose: () => void
  onInstall: (input: InstallSkillInput) => Promise<void>
  isLoading?: boolean
}

type InstallStep = 'source' | 'scan' | 'edit' | 'installing' | 'backend-warn'

/** 风险等级配置 */
const RISK_CONFIG: Record<RiskLevel, { color: string; icon: React.ReactNode; label: string }> = {
  critical: { color: '#ff4d4f', icon: <CloseCircleOutlined />, label: '严重' },
  high: { color: '#fa8c16', icon: <WarningOutlined />, label: '高危' },
  medium: { color: '#faad14', icon: <WarningOutlined />, label: '中危' },
  low: { color: '#1890ff', icon: <InfoCircleOutlined />, label: '低危' },
  info: { color: '#8c8c8c', icon: <InfoCircleOutlined />, label: '信息' },
}

/** 判定结果配置 */
const VERDICT_CONFIG: Record<string, { color: string; icon: React.ReactNode; text: string }> = {
  safe: { color: 'success', icon: <CheckCircleOutlined />, text: '✅ 安全，可以安装' },
  caution: { color: 'warning', icon: <WarningOutlined />, text: '⚠️ 存在风险，建议检查后再安装' },
  danger: { color: 'error', icon: <CloseCircleOutlined />, text: '❌ 检测到高危风险，不建议安装' },
}

export function SkillInstall({ open, onClose, onInstall, isLoading }: SkillInstallProps) {
  const [step, setStep] = useState<InstallStep>('source')
  const folderInputRef = useRef<HTMLInputElement>(null)
  const [parsed, setParsed] = useState<SkillFolderParsed | null>(null)
  const [githubUrl, setGithubUrl] = useState('')
  const [githubChecking, setGithubChecking] = useState(false)
  const [repoCheckResult, setRepoCheckResult] = useState<import('../utils/skill-folder-parser').GitHubRepoCheck | null>(null)

  // 编辑表单
  const [formName, setFormName] = useState('')
  const [formDisplayName, setFormDisplayName] = useState('')
  const [formDescription, setFormDescription] = useState('')
  const [formVersion, setFormVersion] = useState('1.0.0')
  const [formTriggerWords, setFormTriggerWords] = useState('')
  const [formDependencies, setFormDependencies] = useState('')

  // 安装状态
  const [installing, setInstalling] = useState(false)
  const [backendScanResult, setBackendScanResult] = useState<ScanResult | null>(null)
  const [zipBlob, setZipBlob] = useState<Blob | null>(null)

  const resetState = useCallback(() => {
    setStep('source')
    setParsed(null)
    setGithubUrl('')
    setGithubChecking(false)
    setRepoCheckResult(null)
    setFormName('')
    setFormDisplayName('')
    setFormDescription('')
    setFormVersion('1.0.0')
    setFormTriggerWords('')
    setFormDependencies('')
    setInstalling(false)
    setBackendScanResult(null)
    setZipBlob(null)
  }, [])

  const handleClose = useCallback(() => {
    // 如果有已解压的文件（后端扫描有问题但用户取消），清理后端文件
    if (backendScanResult && formName) {
      cleanupSkillDir(formName).catch(() => {})
    }
    resetState()
    onClose()
  }, [resetState, onClose, backendScanResult, formName])

  // ─── JSZip 打包 ──────────────────────────────
  const packageAsZip = useCallback(async (files: { path: string; content: string }[]): Promise<Blob> => {
    const zip = new JSZip()
    for (const file of files) {
      // content 是 base64，需要解码为二进制
      try {
        const binary = atob(file.content)
        const bytes = new Uint8Array(binary.length)
        for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i)
        zip.file(file.path, bytes)
      } catch {
        // 如果 base64 解码失败，当作纯文本
        zip.file(file.path, file.content)
      }
    }
    return zip.generateAsync({ type: 'blob' })
  }, [])

  // ─── 文件夹选择 ──────────────────────────────
  const handleFolderSelect = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const fileList = e.target.files
    if (!fileList || fileList.length === 0) return
    try {
      const result = await parseSkillFolder(fileList)
      setParsed(result)
      setFormName(result.folderName)
      setFormDisplayName(result.extractedName ?? result.folderName)
      setFormDescription(result.extractedDescription ?? '')
      setFormVersion(result.extractedVersion ?? '1.0.0')
      setFormTriggerWords(result.extractedTriggerWords?.join(', ') ?? '')
      setFormDependencies(result.extractedDependencies?.join(', ') ?? '')
      setStep('scan')
    } catch {
      message.error('解析文件夹失败，请检查内容')
    }
    e.target.value = ''
  }, [])

  // ─── GitHub 导入 ──────────────────────────────
  const handleGithubImport = useCallback(async () => {
    if (!githubUrl.trim()) {
      message.warning('请输入 GitHub 仓库地址')
      return
    }
    const rawUrl = githubUrl.trim()
    const decodedUrl = decodeURIComponent(rawUrl)
    const repoName = decodeURIComponent(rawUrl.split('/').pop()?.replace('.git', '') || 'imported-skill')
    setFormName(repoName)
    setFormDisplayName(repoName)
    setFormDescription(`从 GitHub 导入: ${decodedUrl}`)
    setFormVersion('1.0.0')
    setFormTriggerWords('')
    setFormDependencies('')

    const repoPath = githubUrl.trim()
      .replace(/^https?:\/\/github\.com\//, '')
      .replace(/\.git$/, '')
      .replace(/^git@github\.com:/, '')
    if (repoPath.includes('/') && !repoPath.startsWith('http')) {
      setGithubChecking(true)
      try {
        const repoCheck = await checkGitHubRepo(repoPath)
        setRepoCheckResult(repoCheck)
      } catch {
        setRepoCheckResult({ stars: 0, forks: 0, lastPush: '', openIssues: 0, warnings: ['网络请求失败'], verdict: 'unknown' })
      } finally {
        setGithubChecking(false)
      }
      return
    }

    setParsed(null)
    setStep('edit')
  }, [githubUrl])

  // ─── 确认安装（点安装按钮后） ──────────────────
  const handleConfirm = useCallback(async () => {
    if (!formName.trim()) { message.warning('请输入技能名称'); return }
    if (!formDescription.trim()) { message.warning('请输入技能简介'); return }

    const triggerWords = formTriggerWords.split(/[,，]/).map((w) => w.trim()).filter(Boolean)
    const dependencies = formDependencies.split(/[,，]/).map((d) => d.trim()).filter(Boolean)
    const name = formName.trim()
    const displayName = formDisplayName.trim() || name
    const description = formDescription.trim()
    const version = formVersion.trim() || '1.0.0'

    // 有 parsed（文件夹安装）→ 打包 zip 上传到后端
    if (parsed) {
      setInstalling(true)
      setStep('installing')
      try {
        const blob = await packageAsZip(parsed.files)
        setZipBlob(blob)

        const result = await installSkillZip({
          zipBlob: blob,
          name,
          displayName,
          description,
          version,
          source: 'folder',
          triggerWords,
          dependencies,
        })

        if (result.installed) {
          message.success(`已安装技能: ${name}`)
          await onInstall({
            source: 'folder',
            name,
            displayName,
            description,
            version,
            triggerWords,
            dependencies,
            content: '', // 后端已处理，这里只是触发前端刷新
          })
          handleClose()
        } else {
          // 后端扫描有问题，展示后端扫描报告
          setBackendScanResult(result.scanResult ?? null)
          setStep('backend-warn')
        }
      } catch (err: any) {
        message.error(err?.message || '安装失败，请重试')
        setStep('edit')
      } finally {
        setInstalling(false)
      }
      return
    }

    // GitHub 导入 → 走原有的 onInstall（base64 方式）
    try {
      await onInstall({
        source: 'github',
        name,
        displayName,
        description,
        version,
        triggerWords,
        dependencies,
        content: githubUrl.trim(),
      })
      message.success(`已安装技能: ${name}`)
      handleClose()
    } catch {
      message.error('安装失败，请重试')
    }
  }, [formName, formDisplayName, formDescription, formVersion, formTriggerWords, formDependencies, parsed, githubUrl, onInstall, handleClose, packageAsZip])

  // ─── 后端扫描有问题：忽略风险继续安装 ──────────
  const handleForceInstall = useCallback(async () => {
    if (!zipBlob) return
    setInstalling(true)
    try {
      const triggerWords = formTriggerWords.split(/[,，]/).map((w) => w.trim()).filter(Boolean)
      const dependencies = formDependencies.split(/[,，]/).map((d) => d.trim()).filter(Boolean)

      await confirmInstallZip({
        zipBlob,
        name: formName.trim(),
        displayName: formDisplayName.trim() || formName.trim(),
        description: formDescription.trim(),
        version: formVersion.trim() || '1.0.0',
        source: 'folder',
        triggerWords,
        dependencies,
      })

      message.success(`已安装技能: ${formName.trim()}（已忽略风险）`)
      await onInstall({
        source: 'folder',
        name: formName.trim(),
        displayName: formDisplayName.trim() || formName.trim(),
        description: formDescription.trim(),
        version: formVersion.trim() || '1.0.0',
        triggerWords,
        dependencies,
        content: '',
      })
      handleClose()
    } catch (err: any) {
      message.error(err?.message || '安装失败，请重试')
    } finally {
      setInstalling(false)
    }
  }, [zipBlob, formName, formDisplayName, formDescription, formVersion, formTriggerWords, formDependencies, onInstall, handleClose])

  // ─── 后端扫描有问题：取消安装 ──────────────────
  const handleCancelInstall = useCallback(() => {
    cleanupSkillDir(formName).catch(() => {})
    resetState()
    onClose()
  }, [formName, resetState, onClose])

  // ─── 扫描报告渲染 ──────────────────────────────
  const renderScanReport = useCallback((scanResult: ScanResult) => {
    const { issues, summary, verdict, fileCount } = scanResult
    const verdictCfg = VERDICT_CONFIG[verdict]

    const grouped: Record<RiskLevel, typeof issues> = { critical: [], high: [], medium: [], low: [], info: [] }
    for (const issue of issues) grouped[issue.level].push(issue)

    return (
      <div className={styles.scanReport}>
        <Alert
          type={verdictCfg.color as 'success' | 'warning' | 'error'}
          showIcon
          icon={verdictCfg.icon}
          title={<strong>{verdictCfg.text}</strong>}
          description={`扫描 ${fileCount} 个文件，发现 ${issues.length} 个问题`}
          style={{ marginBottom: 16 }}
        />

        <div className={styles.scanSummary}>
          {(Object.entries(summary) as [RiskLevel, number][]).map(([level, count]) => (
            count > 0 && (
              <div key={level} className={styles.scanSummaryItem}>
                <span style={{ color: RISK_CONFIG[level].color, fontWeight: 600 }}>{count}</span>
                <span style={{ fontSize: 12, color: '#8c8c8c' }}>{RISK_CONFIG[level].label}</span>
              </div>
            )
          ))}
        </div>

        {issues.length > 0 && (
          <div className={styles.scanIssues}>
            {(['critical', 'high', 'medium', 'low', 'info'] as RiskLevel[]).map((level) =>
              grouped[level].length > 0 ? (
                <div key={level} className={styles.scanIssueGroup}>
                  <div className={styles.scanIssueGroupTitle} style={{ color: RISK_CONFIG[level].color }}>
                    {RISK_CONFIG[level].icon} {RISK_CONFIG[level].label}（{grouped[level].length}）
                  </div>
                  {grouped[level].map((issue, i) => (
                    <div key={i} className={styles.scanIssueItem}>
                      <div className={styles.scanIssueCategory}>{issue.category}</div>
                      <div className={styles.scanIssueMessage}>{issue.message}</div>
                      {issue.file && (
                        <div className={styles.scanIssueFile}>
                          <FileOutlined style={{ marginRight: 4 }} />
                          {issue.file}{issue.line ? `:${issue.line}` : ''}
                        </div>
                      )}
                      {issue.snippet && (
                        <code className={styles.scanIssueSnippet}>{issue.snippet}</code>
                      )}
                    </div>
                  ))}
                </div>
              ) : null
            )}
          </div>
        )}
      </div>
    )
  }, [])

  // ─── 主渲染 ──────────────────────────────
  const stepIndex = step === 'source' ? 0 : step === 'scan' ? 1 : step === 'edit' || step === 'installing' || step === 'backend-warn' ? 2 : 0

  return (
    <Drawer
      title="📦 安装技能"
      open={open}
      onClose={handleClose}
      size={480}
      destroyOnHidden
      footer={
        step === 'scan' ? (
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <Button onClick={() => setStep('source')}>上一步</Button>
            <Space>
              <Button onClick={handleClose}>取消</Button>
              {parsed?.scanResult.verdict === 'danger' ? (
                <Button type="primary" danger onClick={() => setStep('edit')}>
                  忽略风险，继续安装
                </Button>
              ) : (
                <Button type="primary" onClick={() => setStep('edit')}>
                  继续安装
                </Button>
              )}
            </Space>
          </div>
        ) : step === 'edit' ? (
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <Button onClick={() => parsed ? setStep('scan') : setStep('source')}>上一步</Button>
            <Space>
              <Button onClick={handleClose}>取消</Button>
              <Button type="primary" onClick={() => void handleConfirm()} loading={installing}>
                确认安装
              </Button>
            </Space>
          </div>
        ) : step === 'installing' ? (
          <div style={{ display: 'flex', justifyContent: 'center', padding: '12px 0' }}>
            <Spin indicator={<LoadingOutlined style={{ fontSize: 20 }} spin />} />
            <Text style={{ marginLeft: 12 }}>正在安装，请稍候...</Text>
          </div>
        ) : step === 'backend-warn' ? (
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <Button onClick={handleCancelInstall}>取消安装</Button>
            <Space>
              <Button onClick={handleCancelInstall}>取消</Button>
              <Button type="primary" danger onClick={() => void handleForceInstall()} loading={installing}>
                忽略风险，继续安装
              </Button>
            </Space>
          </div>
        ) : undefined
      }
    >
      <Steps
        current={stepIndex}
        size="small"
        items={[{ title: '选择来源' }, { title: '安全检查' }, { title: '确认安装' }]}
        style={{ marginBottom: 24 }}
      />

      {/* ─── 步骤一：选择来源 ──────────────────── */}
      {step === 'source' && (
        <div className={styles.installContent}>
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
            >
              <p style={{ fontSize: 32, margin: 0 }}>📂</p>
              <p style={{ margin: '8px 0 4px', fontWeight: 500 }}>点击选择技能文件夹</p>
              <Text type="secondary" style={{ fontSize: 12 }}>
                文件夹名将作为技能名称，选择后自动进行安全扫描
              </Text>
            </div>
          </div>

          <Divider plain>或</Divider>

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
                disabled={githubChecking}
              />
              <Button type="primary" onClick={() => void handleGithubImport()} loading={githubChecking}>
                {githubChecking ? '检查仓库信誉中...' : '下一步'}
              </Button>
            </div>
            <Text type="secondary" style={{ fontSize: 12 }}>
              格式：user/repo 或 https://github.com/user/repo
            </Text>

            {repoCheckResult && (
              <div style={{ marginTop: 16 }}>
                <Alert
                  type={repoCheckResult.verdict === 'trusted' ? 'success' : repoCheckResult.verdict === 'caution' ? 'warning' : 'info'}
                  showIcon
                  icon={repoCheckResult.verdict === 'trusted' ? <CheckCircleOutlined /> : <WarningOutlined />}
                  message={<strong>仓库信誉检查</strong>}
                  description={
                    <div style={{ marginTop: 8 }}>
                      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginBottom: 12 }}>
                        <div>
                          <span style={{ color: repoCheckResult.stars >= 10 ? '#52c41a' : repoCheckResult.stars >= 5 ? '#faad14' : '#ff4d4f', fontWeight: 600 }}>
                            {repoCheckResult.stars >= 10 ? '✅' : repoCheckResult.stars >= 5 ? '⚠️' : '❌'} ⭐ {repoCheckResult.stars} Stars
                          </span>
                        </div>
                        <div>
                          <span style={{ color: repoCheckResult.forks >= 5 ? '#52c41a' : repoCheckResult.forks >= 2 ? '#faad14' : '#ff4d4f', fontWeight: 600 }}>
                            {repoCheckResult.forks >= 5 ? '✅' : repoCheckResult.forks >= 2 ? '⚠️' : '❌'} 🍴 {repoCheckResult.forks} Forks
                          </span>
                        </div>
                        <div>
                          <span style={{ fontWeight: 600 }}>
                            {repoCheckResult.lastPush
                              ? (() => {
                                  const days = Math.floor((Date.now() - new Date(repoCheckResult.lastPush).getTime()) / (1000 * 60 * 60 * 24))
                                  return days < 30
                                    ? `✅ 📅 ${days} 天前更新`
                                    : days < 180
                                    ? `⚠️ 📅 ${days} 天前更新`
                                    : `❌ 📅 ${days} 天前更新（可能已废弃）`
                                })()
                              : '❌ 📅 更新时间未知'}
                          </span>
                        </div>
                      </div>
                      {repoCheckResult.warnings.length > 0 && (
                        <div style={{ borderTop: '1px solid #f0f0f0', paddingTop: 8 }}>
                          {repoCheckResult.warnings.map((w, i) => (
                            <div key={i} style={{ color: '#fa8c16', fontSize: 13, marginBottom: 4 }}>⚠️ {w}</div>
                          ))}
                        </div>
                      )}
                      {repoCheckResult.warnings.length === 0 && (
                        <div style={{ color: '#52c41a', fontSize: 13 }}>✅ 未发现信誉问题</div>
                      )}
                    </div>
                  }
                  style={{ marginBottom: 12 }}
                />
                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
                  <Button onClick={() => { setRepoCheckResult(null); setGithubUrl('') }}>重新输入</Button>
                  {repoCheckResult.verdict === 'caution' ? (
                    <Button type="primary" danger onClick={() => { setRepoCheckResult(null); setParsed(null); setStep('edit') }}>
                      忽略风险，继续安装
                    </Button>
                  ) : (
                    <Button type="primary" onClick={() => { setRepoCheckResult(null); setParsed(null); setStep('edit') }}>
                      继续安装
                    </Button>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ─── 步骤二：前端安全扫描报告 ────────────── */}
      {step === 'scan' && parsed && (
        <div className={styles.installContent}>
          <div className={styles.folderPreview}>
            <FolderOpenOutlined style={{ marginRight: 8 }} />
            <Text strong>{parsed.folderName}/</Text>
            <Text type="secondary" style={{ marginLeft: 8, fontSize: 12 }}>
              {parsed.files.length} 个文件
            </Text>
          </div>
          {renderScanReport(parsed.scanResult)}
        </div>
      )}

      {/* ─── 步骤三：编辑确认 ──────────────────── */}
      {step === 'edit' && (
        <div className={styles.installContent}>
          {parsed && (
            <div className={styles.folderPreview}>
              <FileOutlined style={{ marginRight: 8 }} />
              <Text strong>{parsed.folderName}/</Text>
              <Text type="secondary" style={{ marginLeft: 8, fontSize: 12 }}>
                {parsed.files.length} 个文件
              </Text>
            </div>
          )}

          <div className={styles.installSection}>
            <label className={styles.formLabel}>
              技能名称 <span className={styles.required}>*</span>
            </label>
            <Input value={formName} onChange={(e) => setFormName(e.target.value)} placeholder="英文、数字、连字符" />
          </div>

          <div className={styles.installSection}>
            <label className={styles.formLabel}>显示名称</label>
            <Input value={formDisplayName} onChange={(e) => setFormDisplayName(e.target.value)} placeholder="用于界面展示的友好名称" />
          </div>

          <div className={styles.installSection}>
            <label className={styles.formLabel}>
              技能简介 <span className={styles.required}>*</span>
            </label>
            <Input.TextArea
              value={formDescription}
              onChange={(e) => setFormDescription(e.target.value)}
              placeholder="描述这个技能的用途和功能"
              autoSize={{ minRows: 2, maxRows: 4 }}
              showCount
              maxLength={1024}
            />
          </div>

          <div className={styles.installSection}>
            <label className={styles.formLabel}>版本号</label>
            <Input value={formVersion} onChange={(e) => setFormVersion(e.target.value)} placeholder="1.0.0" style={{ width: 120 }} />
          </div>

          <div className={styles.installSection}>
            <label className={styles.formLabel}>触发词</label>
            <Input value={formTriggerWords} onChange={(e) => setFormTriggerWords(e.target.value)} placeholder="用逗号分隔，如: debug, 排查" />
            {formTriggerWords && (
              <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginTop: 4 }}>
                {formTriggerWords.split(/[,，]/).map((w) => w.trim()).filter(Boolean).map((word) => (
                  <Tag key={word} color="orange" style={{ fontSize: 11 }}>{word}</Tag>
                ))}
              </div>
            )}
          </div>

          <div className={styles.installSection}>
            <label className={styles.formLabel}>依赖技能</label>
            <Input value={formDependencies} onChange={(e) => setFormDependencies(e.target.value)} placeholder="用逗号分隔，如: tdd, writing-plans" />
            {formDependencies && (
              <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginTop: 4 }}>
                {formDependencies.split(/[,，]/).map((d) => d.trim()).filter(Boolean).map((dep) => (
                  <Tag key={dep} style={{ fontSize: 11 }}>{dep}</Tag>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ─── 安装中 loading ──────────────────────── */}
      {step === 'installing' && (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '48px 0' }}>
          <Spin size="large" indicator={<LoadingOutlined style={{ fontSize: 48 }} spin />} />
          <Text style={{ marginTop: 16, fontSize: 16 }}>正在安装技能...</Text>
          <Text type="secondary" style={{ marginTop: 8 }}>后端正在解压、扫描并安装，请稍候</Text>
        </div>
      )}

      {/* ─── 后端扫描有问题：展示报告 ────────────── */}
      {step === 'backend-warn' && backendScanResult && (
        <div className={styles.installContent}>
          <Alert
            type="warning"
            showIcon
            icon={<WarningOutlined />}
            title={<strong>后端安全扫描发现问题</strong>}
            description="以下问题由后端全面扫描发现，请确认是否忽略风险继续安装。"
            style={{ marginBottom: 16 }}
          />
          {renderScanReport(backendScanResult)}
        </div>
      )}
    </Drawer>
  )
}
