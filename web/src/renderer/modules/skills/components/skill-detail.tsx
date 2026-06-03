/** 技能详情组件（Drawer）— 支持查看 / 编辑模式切换 */

import { useState, useCallback, useEffect } from 'react'
import { Drawer, Tag, Divider, Button, Input, Space, message, Popconfirm } from 'antd'
import {
  ThunderboltOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  CalendarOutlined,
  LinkOutlined,
  EditOutlined,
  DeleteOutlined,
} from '@ant-design/icons'
import type { Skill, UpdateSkillInput } from '../types/skills'
import styles from './skills-panel.module.css'

interface SkillDetailProps {
  open: boolean
  skill: Skill | null
  onClose: () => void
  onRefine?: (skill: Skill) => void
  onUpdate?: (id: number, input: UpdateSkillInput) => Promise<void>
  onDelete?: (id: number) => Promise<void>
}

/** 格式化耗时 */
function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

/** 格式化日期 */
function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  })
}

/** Mock SKILL.md 内容 */
function getMockSkillMd(skill: Skill): string {
  return `# ${skill.name}

> ${skill.description}

## 版本

v${skill.version}

## 触发词

${(skill.triggerWords ?? []).map((w) => `- \`${w}\``).join('\n') || '无'}

## 使用示例

当用户提到相关触发词时，此技能会自动激活。

## 依赖

${(skill.dependencies ?? []).length > 0 ? (skill.dependencies ?? []).map((d) => `- ${d}`).join('\n') : '无外部依赖'}
`
}

/** 技能详情 Drawer */
export function SkillDetail({ open, skill, onClose, onRefine, onUpdate, onDelete }: SkillDetailProps) {
  // ─── 编辑模式 ──────────────────────────────
  const [editing, setEditing] = useState(false)
  const [editDisplayName, setEditDisplayName] = useState('')
  const [editDescription, setEditDescription] = useState('')
  const [editVersion, setEditVersion] = useState('')
  const [editTriggerWords, setEditTriggerWords] = useState('')
  const [editDependencies, setEditDependencies] = useState('')
  const [saving, setSaving] = useState(false)

  // 进入编辑模式时填充表单
  useEffect(() => {
    if (skill && editing) {
      setEditDisplayName(skill.displayName || skill.name)
      setEditDescription(skill.description)
      setEditVersion(skill.version)
      setEditTriggerWords(skill.triggerWords?.join(', ') ?? '')
      setEditDependencies(skill.dependencies?.join(', ') ?? '')
    }
  }, [skill, editing])

  const handleEditStart = useCallback(() => {
    setEditing(true)
  }, [])

  const handleEditCancel = useCallback(() => {
    setEditing(false)
  }, [])

  const handleSave = useCallback(async () => {
    if (!skill || !onUpdate) return
    if (!editDescription.trim()) {
      message.warning('请输入技能简介')
      return
    }

    setSaving(true)
    try {
      await onUpdate(skill.id, {
        displayName: editDisplayName.trim() || skill.name,
        description: editDescription.trim(),
        version: editVersion.trim() || '1.0.0',
        triggerWords: editTriggerWords.split(/[,，]/).map((w) => w.trim()).filter(Boolean),
        dependencies: editDependencies.split(/[,，]/).map((d) => d.trim()).filter(Boolean),
      })
      message.success('保存成功')
      setEditing(false)
    } catch {
      message.error('保存失败，请重试')
    } finally {
      setSaving(false)
    }
  }, [skill, onUpdate, editDisplayName, editDescription, editVersion, editTriggerWords, editDependencies])

  const handleDelete = useCallback(async () => {
    if (!skill || !onDelete) return
    try {
      await onDelete(skill.id)
      message.success('已删除')
      onClose()
    } catch {
      message.error('删除失败，请重试')
    }
  }, [skill, onDelete, onClose])

  if (!skill) return null

  const skillMd = getMockSkillMd(skill)

  return (
    <Drawer
      title={editing ? `✏️ 编辑 ${skill.name}` : `🔧 ${skill.name}`}
      open={open}
      onClose={() => {
        setEditing(false)
        onClose()
      }}
      width={500}
      destroyOnClose
      footer={
        editing ? (
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
            <Button onClick={handleEditCancel}>取消</Button>
            <Button type="primary" onClick={() => void handleSave()} loading={saving}>
              保存
            </Button>
          </div>
        ) : onUpdate ? (
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            {onDelete ? (
              <Popconfirm
                title="确认删除此技能？"
                description="删除后不可恢复"
                onConfirm={() => void handleDelete()}
                okText="删除"
                cancelText="取消"
                okButtonProps={{ danger: true }}
              >
                <Button danger icon={<DeleteOutlined />}>
                  删除
                </Button>
              </Popconfirm>
            ) : (
              <span />
            )}
            <Space>
              {onRefine && (
                <Button onClick={() => onRefine(skill)}>🧪 炼化</Button>
              )}
              <Button type="primary" icon={<EditOutlined />} onClick={handleEditStart}>
                编辑
              </Button>
            </Space>
          </div>
        ) : undefined
      }
    >
      <div className={styles.detailContent}>
        {editing ? (
          /* ─── 编辑模式 ──────────────────────────── */
          <>
            <div className={styles.detailSection}>
              <label className={styles.formLabel}>显示名称</label>
              <Input
                value={editDisplayName}
                onChange={(e) => setEditDisplayName(e.target.value)}
                placeholder="用于界面展示的友好名称"
                disabled={saving}
              />
            </div>

            <div className={styles.detailSection}>
              <label className={styles.formLabel}>
                技能简介 <span className={styles.required}>*</span>
              </label>
              <Input.TextArea
                value={editDescription}
                onChange={(e) => setEditDescription(e.target.value)}
                placeholder="描述这个技能的用途和功能"
                autoSize={{ minRows: 2, maxRows: 4 }}
                disabled={saving}
                showCount
                maxLength={1024}
              />
            </div>

            <div className={styles.detailSection}>
              <label className={styles.formLabel}>版本号</label>
              <Input
                value={editVersion}
                onChange={(e) => setEditVersion(e.target.value)}
                placeholder="1.0.0"
                disabled={saving}
                style={{ width: 120 }}
              />
            </div>

            <div className={styles.detailSection}>
              <label className={styles.formLabel}>触发词</label>
              <Input
                value={editTriggerWords}
                onChange={(e) => setEditTriggerWords(e.target.value)}
                placeholder="用逗号分隔，如: debug, 排查, 诊断"
                disabled={saving}
              />
              {editTriggerWords && (
                <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginTop: 4 }}>
                  {editTriggerWords.split(/[,，]/).map((w) => w.trim()).filter(Boolean).map((word) => (
                    <Tag key={word} color="orange" style={{ fontSize: 11 }}>
                      {word}
                    </Tag>
                  ))}
                </div>
              )}
            </div>

            <div className={styles.detailSection}>
              <label className={styles.formLabel}>依赖技能</label>
              <Input
                value={editDependencies}
                onChange={(e) => setEditDependencies(e.target.value)}
                placeholder="用逗号分隔，如: tdd, writing-plans"
                disabled={saving}
              />
              {editDependencies && (
                <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginTop: 4 }}>
                  {editDependencies.split(/[,，]/).map((d) => d.trim()).filter(Boolean).map((dep) => (
                    <Tag key={dep} style={{ fontSize: 11 }}>
                      {dep}
                    </Tag>
                  ))}
                </div>
              )}
            </div>
          </>
        ) : (
          /* ─── 查看模式 ──────────────────────────── */
          <>
            {/* 基本信息 */}
            <div className={styles.detailSection}>
              <div className={styles.detailRow}>
                <span className={styles.detailRowLabel}>版本</span>
                <Tag color="blue">{skill.version}</Tag>
              </div>
              <div className={styles.detailRow}>
                <span className={styles.detailRowLabel}>创建日期</span>
                <span className={styles.detailRowValue}>
                  <CalendarOutlined style={{ marginRight: 4 }} />
                  {formatDate(skill.createdAt)}
                </span>
              </div>
              <div className={styles.detailRow}>
                <span className={styles.detailRowLabel}>状态</span>
                <Tag color={skill.isEnabled ? 'green' : 'default'}>
                  {skill.isEnabled ? '已启用' : '已禁用'}
                </Tag>
              </div>
            </div>

            {/* 使用统计 */}
            <div className={styles.detailSection}>
              <span className={styles.detailLabel}>使用统计</span>
              <div className={styles.statsGrid}>
                <div className={styles.statCard}>
                  <div className={styles.statValue}>{skill.stats?.callCount ?? 0}</div>
                  <div className={styles.statLabel}>
                    <ThunderboltOutlined /> 调用次数
                  </div>
                </div>
                <div className={styles.statCard}>
                  <div className={styles.statValue}>
                    {skill.stats
                      ? ((skill.stats.callCount > 0
                          ? skill.stats.successCount / skill.stats.callCount
                          : 0) * 100
                        ).toFixed(0)
                      : 0}
                    %
                  </div>
                  <div className={styles.statLabel}>
                    <CheckCircleOutlined /> 成功率
                  </div>
                </div>
                <div className={styles.statCard}>
                  <div className={styles.statValue}>
                    {formatDuration(skill.stats?.avgDurationMs ?? 0)}
                  </div>
                  <div className={styles.statLabel}>
                    <ClockCircleOutlined /> 平均耗时
                  </div>
                </div>
              </div>
            </div>

            {/* 依赖 */}
            {(skill.dependencies ?? []).length > 0 && (
              <div className={styles.detailSection}>
                <span className={styles.detailLabel}>
                  <LinkOutlined /> 依赖
                </span>
                <div className={styles.dependencies}>
                  {(skill.dependencies ?? []).map((dep) => (
                    <Tag key={dep} className={styles.depTag}>
                      {dep}
                    </Tag>
                  ))}
                </div>
              </div>
            )}

            {/* 触发词 */}
            <div className={styles.detailSection}>
              <span className={styles.detailLabel}>触发词</span>
              <div className={styles.dependencies}>
                {(skill.triggerWords ?? []).map((word) => (
                  <Tag key={word} color="orange" className={styles.depTag}>
                    {word}
                  </Tag>
                ))}
              </div>
            </div>

            <Divider />

            {/* SKILL.md 内容 */}
            <div className={styles.detailSection}>
              <span className={styles.detailLabel}>SKILL.md</span>
              <div className={styles.markdownContent}>{skillMd}</div>
            </div>
          </>
        )}
      </div>
    </Drawer>
  )
}
