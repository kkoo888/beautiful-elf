/** 专家绑定技能弹窗 — 从技能列表中选择绑定 */

import { useState, useEffect, useCallback } from 'react'
import {
  Modal,
  Checkbox,
  Space,
  Tag,
  Typography,
  Input,
  Spin,
  Empty,
} from 'antd'
import { ThunderboltOutlined } from '@ant-design/icons'
import type { Skill } from '@/modules/skills/types/skills'
import type { ExpertSkill } from '../types'
import styles from './expert-team.module.css'

const { Text } = Typography
const { Search } = Input

interface ExpertBindSkillsModalProps {
  open: boolean
  /** 所有可用技能 */
  skills: Skill[]
  /** 已绑定的技能绑定记录 */
  boundSkills: ExpertSkill[]
  loading?: boolean
  onOk: (skillIds: number[]) => void
  onCancel: () => void
}

export function ExpertBindSkillsModal({
  open,
  skills,
  boundSkills,
  loading,
  onOk,
  onCancel,
}: ExpertBindSkillsModalProps) {
  const [selectedIds, setSelectedIds] = useState<number[]>([])
  const [search, setSearch] = useState('')

  // 打开时初始化选中状态
  useEffect(() => {
    if (open) {
      setSelectedIds(boundSkills.map((s) => s.skillId))
      setSearch('')
    }
  }, [open, boundSkills])

  const handleToggle = useCallback((skillId: number) => {
    setSelectedIds((prev) =>
      prev.includes(skillId) ? prev.filter((id) => id !== skillId) : [...prev, skillId],
    )
  }, [])

  const handleOk = useCallback(() => {
    onOk(selectedIds)
  }, [selectedIds, onOk])

  // 过滤后的技能列表
  const filtered = skills.filter((s) => {
    if (!search) return true
    const q = search.toLowerCase()
    return (
      s.name.toLowerCase().includes(q) ||
      s.displayName.toLowerCase().includes(q) ||
      s.description.toLowerCase().includes(q) ||
      s.triggerWords?.some((w) => w.toLowerCase().includes(q))
    )
  })

  // 已绑定的 skillId 集合
  const boundSet = new Set(boundSkills.map((s) => s.skillId))

  return (
    <Modal
      open={open}
      title="绑定技能"
      onOk={handleOk}
      onCancel={onCancel}
      width={560}
      okText={`确定 (${selectedIds.length})`}
      cancelText="取消"
    >
      <div style={{ marginBottom: 12 }}>
        <Search
          placeholder="搜索技能名称、触发词..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          allowClear
        />
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '40px 0' }}>
          <Spin />
        </div>
      ) : filtered.length === 0 ? (
        <Empty description="没有可用的技能" />
      ) : (
        <div style={{ maxHeight: 400, overflow: 'auto' }}>
          {filtered.map((skill) => {
            const checked = selectedIds.includes(skill.id)
            const alreadyBound = boundSet.has(skill.id)
            return (
              <div
                key={skill.id}
                className={styles.memberListCard}
                style={{
                  borderLeft: `3px solid ${checked ? '#1890ff' : '#f0f0f0'}`,
                  cursor: 'pointer',
                  opacity: skill.isEnabled ? 1 : 0.5,
                }}
                onClick={() => handleToggle(skill.id)}
              >
                <div className={styles.memberListCardHeader}>
                  <Checkbox checked={checked} />
                  <div style={{ marginLeft: 8, flex: 1, minWidth: 0 }}>
                    <Space>
                      <ThunderboltOutlined style={{ color: '#1890ff' }} />
                      <Text strong>{skill.displayName || skill.name}</Text>
                      {alreadyBound && <Tag color="blue">已绑定</Tag>}
                      {!skill.isEnabled && <Tag color="default">已禁用</Tag>}
                    </Space>
                    {skill.description && (
                      <div style={{ fontSize: 12, color: '#8c8c8c', marginTop: 2 }}>
                        {skill.description.length > 80 ? skill.description.slice(0, 80) + '...' : skill.description}
                      </div>
                    )}
                    {skill.triggerWords?.length > 0 && (
                      <div style={{ marginTop: 4 }}>
                        {skill.triggerWords.slice(0, 5).map((w) => (
                          <Tag key={w} style={{ fontSize: 11 }}>{w}</Tag>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </Modal>
  )
}
