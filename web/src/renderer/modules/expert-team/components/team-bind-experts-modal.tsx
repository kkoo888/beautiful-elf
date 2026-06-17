/** 专家团绑定专家弹窗 — 多选已有专家 */

import { useState, useEffect, useCallback } from 'react'
import {
  Modal,
  Checkbox,
  Space,
  Tag,
  Typography,
  Input,
  Empty,
} from 'antd'
import type { Expert } from '../types'
import { getExpertRoleColor } from '../types'
import { ExpertAvatar } from '@/components/expert-avatar'
import styles from './expert-team.module.css'

const { Text } = Typography

interface TeamBindExpertsModalProps {
  open: boolean
  experts: Expert[]
  /** 当前已绑定的专家 ID */
  boundIds: number[]
  onOk: (expertIds: number[]) => void
  onCancel: () => void
}

export function TeamBindExpertsModal({
  open,
  experts,
  boundIds,
  onOk,
  onCancel,
}: TeamBindExpertsModalProps) {
  const [selectedIds, setSelectedIds] = useState<number[]>(boundIds)
  const [search, setSearch] = useState('')

  useEffect(() => {
    if (open) {
      setSelectedIds(boundIds)
      setSearch('')
    }
  }, [open, boundIds])

  const filtered = experts.filter(
    (e) =>
      !search ||
      e.memberName.toLowerCase().includes(search.toLowerCase()) ||
      e.memberRole.toLowerCase().includes(search.toLowerCase())
  )

  const handleToggle = useCallback((id: number) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]
    )
  }, [])

  const handleOk = useCallback(() => {
    onOk(selectedIds)
  }, [selectedIds, onOk])

  return (
    <Modal
      open={open}
      title="绑定专家到专家团"
      onOk={handleOk}
      onCancel={onCancel}
      width={560}
      okText="确定"
      cancelText="取消"
      destroyOnHidden
    >
      <div style={{ marginBottom: 12 }}>
        <Input.Search
          placeholder="搜索专家名称或角色..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          allowClear
          size="small"
        />
      </div>

      <div style={{ marginBottom: 8 }}>
        <Text type="secondary" style={{ fontSize: 12 }}>
          已选 {selectedIds.length} 位专家
        </Text>
      </div>

      {filtered.length === 0 ? (
        <Empty description="没有可用的专家，请先在「专家」列表中创建" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      ) : (
        <div style={{ maxHeight: 400, overflowY: 'auto' }}>
          {filtered.map((expert) => {
            const roleColor = getExpertRoleColor(expert.memberRole)
            const checked = selectedIds.includes(expert.id)
            return (
              <div
                key={expert.id}
                className={styles.memberListCard}
                style={{
                  borderLeft: `3px solid ${roleColor}`,
                  cursor: 'pointer',
                  opacity: expert.isEnabled ? 1 : 0.5,
                }}
                onClick={() => handleToggle(expert.id)}
              >
                <div className={styles.memberListCardHeader}>
                  <Checkbox checked={checked} />
                  <ExpertAvatar
                    avatar={expert.avatar}
                    size={40}
                    bgColor={roleColor + '18'}
                    color={roleColor}
                    className={styles.memberAvatar}
                    style={{ marginLeft: 8 }}
                  />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <Space>
                      <Text strong>{expert.memberName}</Text>
                      <Tag color={roleColor} style={{ margin: 0 }}>{expert.memberRole}</Tag>
                      {!expert.isEnabled && <Tag color="default">已禁用</Tag>}
                    </Space>
                  </div>
                </div>
                <p className={styles.memberPrompt}>
                  {expert.systemPrompt?.slice(0, 100) || '暂无提示词'}
                  {(expert.systemPrompt?.length || 0) > 100 ? '...' : ''}
                </p>
              </div>
            )
          })}
        </div>
      )}
    </Modal>
  )
}
