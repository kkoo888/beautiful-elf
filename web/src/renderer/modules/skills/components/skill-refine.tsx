/** 炼化面板组件（Drawer） */

import { useState, useCallback } from 'react'
import { Drawer, Input, Button, Spin, App, Typography } from 'antd'
import { BulbOutlined, EditOutlined, SaveOutlined } from '@ant-design/icons'
import type { Skill, RefineResult } from '../types/skills'
import styles from './skills-panel.module.css'

const { TextArea } = Input
const { Text } = Typography

interface SkillRefineProps {
  open: boolean
  skill: Skill | null
  onClose: () => void
  onRefine: (id: number, prompt?: string) => Promise<RefineResult>
  isRefining?: boolean
}

/** 炼化面板 Drawer */
export function SkillRefine({ open, skill, onClose, onRefine, isRefining }: SkillRefineProps) {
  const { message } = App.useApp()
  const [prompt, setPrompt] = useState('')
  const [result, setResult] = useState<RefineResult | null>(null)
  const [editedContent, setEditedContent] = useState('')
  const [isEditing, setIsEditing] = useState(false)

  const handleRefine = useCallback(async () => {
    if (!skill) return
    try {
      const res = await onRefine(skill.id, prompt || undefined)
      setResult(res)
      setEditedContent(res.refinedContent)
      setIsEditing(false)
    } catch {
      message.error('炼化失败，请重试')
    }
  }, [skill, prompt, onRefine])

  const handleClose = useCallback(() => {
    setPrompt('')
    setResult(null)
    setEditedContent('')
    setIsEditing(false)
    onClose()
  }, [onClose])

  const handleSave = useCallback(() => {
    message.success('已保存优化内容')
    setIsEditing(false)
  }, [])

  if (!skill) return null

  return (
    <Drawer
      title={`✨ 炼化 - ${skill.name}`}
      open={open}
      onClose={handleClose}
      size={520}
      destroyOnHidden
    >
      <div className={styles.refineContent}>
        {/* 优化提示输入 */}
        <div className={styles.detailSection}>
          <span className={styles.detailLabel}>优化提示（可选）</span>
          <TextArea
            className={styles.refineInput}
            placeholder="描述你希望如何优化此技能，例如：增加更多使用示例、改进错误处理..."
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            rows={3}
            disabled={isRefining}
          />
        </div>

        <Button
          type="primary"
          icon={<BulbOutlined />}
          onClick={() => void handleRefine()}
          loading={isRefining}
          block
        >
          {result ? '重新炼化' : '开始炼化'}
        </Button>

        {/* 加载中 */}
        {isRefining && !result && (
          <div className={styles.loading}>
            <Spin description="AI 正在分析技能并生成优化建议..." />
          </div>
        )}

        {/* 优化建议 */}
        {result && (
          <>
            <div className={styles.detailSection}>
              <span className={styles.detailLabel}>💡 优化建议</span>
              <div className={styles.suggestionsList}>
                {result.suggestions.map((s, i) => (
                  <div key={i} className={styles.suggestionItem}>
                    <BulbOutlined className={styles.suggestionIcon} />
                    <span>{s}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* 优化后的内容 */}
            <div className={styles.detailSection}>
              <div
                style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}
              >
                <span className={styles.detailLabel}>优化后的 SKILL.md</span>
                <Button
                  type="text"
                  size="small"
                  icon={isEditing ? <SaveOutlined /> : <EditOutlined />}
                  onClick={isEditing ? handleSave : () => setIsEditing(true)}
                >
                  {isEditing ? '保存' : '编辑'}
                </Button>
              </div>
              {isEditing ? (
                <TextArea
                  value={editedContent}
                  onChange={(e) => setEditedContent(e.target.value)}
                  rows={12}
                  style={{ fontFamily: 'monospace', fontSize: 13 }}
                />
              ) : (
                <div className={styles.refinedContent}>{editedContent}</div>
              )}
            </div>

            <div className={styles.refineActions}>
              <Button onClick={handleClose}>关闭</Button>
              <Button type="primary" onClick={handleSave}>
                应用优化
              </Button>
            </div>
          </>
        )}
      </div>
    </Drawer>
  )
}
