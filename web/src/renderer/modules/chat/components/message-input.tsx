/**
 * 消息输入框组件 — 现代 AI 助手风格
 * 圆角容器包裹、内部工具栏（专家团/技能选择）+ 多行输入区
 */

import React, { useCallback, useEffect, useRef, useState } from 'react'
import { Dropdown, Tooltip } from 'antd'
import type { MenuProps } from 'antd'
import {
  RobotOutlined,
  ThunderboltOutlined,
  AimOutlined,
  SendOutlined,
  StopOutlined,
  CloseOutlined,
  DownOutlined,
} from '@ant-design/icons'
import { fetchExpertTeams } from '@/modules/expert-team/services/expert-team-api'
import type { ExpertTeam } from '@/modules/expert-team/types'
import { ExpertAvatar } from '@/components/expert-avatar'
import { fetchSkills } from '@/modules/skills/services/skills-api'
import type { Skill } from '@/modules/skills/types/skills'
import styles from './chat-panel.module.css'

interface SendOptions {
  expertTeamId?: number
  skillId?: number
  teamMode?: 'off' | 'auto' | 'manual'
  goalMode?: boolean
}

interface MessageInputProps {
  /** 发送消息回调 */
  onSend: (content: string, options?: SendOptions) => void
  /** 是否禁用（正在生成中） */
  disabled?: boolean
  /** 停止生成回调 */
  onStop?: () => void
  /** 是否正在加载 */
  isLoading?: boolean
}

export const MessageInput: React.FC<MessageInputProps> = ({
  onSend,
  disabled = false,
  onStop,
  isLoading = false,
}) => {
  const [value, setValue] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // 专家团 / 技能列表
  const [expertTeams, setExpertTeams] = useState<ExpertTeam[]>([])
  const [skills, setSkills] = useState<Skill[]>([])

  // 当前选中
  const [selectedTeamId, setSelectedTeamId] = useState<number | null>(null)
  const [teamMode, setTeamMode] = useState<'off' | 'auto' | 'manual'>('off')
  const [selectedSkillId, setSelectedSkillId] = useState<number | null>(null)
  const [goalMode, setGoalMode] = useState(false)

  // 加载专家团列表
  useEffect(() => {
    let cancelled = false
    fetchExpertTeams({ enabled: 1 })
      .then(({ items }) => {
        if (!cancelled) setExpertTeams(items)
      })
      .catch(() => {})
    return () => { cancelled = true }
  }, [])

  // 加载技能列表
  useEffect(() => {
    let cancelled = false
    fetchSkills({ isEnabled: 1, pageSize: 100 })
      .then(({ data }) => {
        if (!cancelled) setSkills(data)
      })
      .catch(() => {})
    return () => { cancelled = true }
  }, [])

  // 派生：选中项名称
  const selectedTeamName = teamMode === 'auto'
    ? 'Auto'
    : selectedTeamId
      ? expertTeams.find((t) => t.id === selectedTeamId)?.teamName
      : undefined
  const selectedSkillName = selectedSkillId
    ? skills.find((s) => s.id === selectedSkillId)?.displayName
    : undefined

  /** 自动调整高度 */
  const adjustHeight = useCallback(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`
  }, [])

  /** 发送消息 */
  const handleSend = useCallback(() => {
    const trimmed = value.trim()
    if (!trimmed || disabled) return

    const options: SendOptions = {}
    if (teamMode === 'auto') {
      options.teamMode = 'auto'
    } else if (teamMode === 'manual' && selectedTeamId != null) {
      options.teamMode = 'manual'
      options.expertTeamId = selectedTeamId
    }
    if (selectedSkillId != null) options.skillId = selectedSkillId
    if (goalMode) options.goalMode = true

    onSend(trimmed, options)
    setValue('')

    // 重置高度
    requestAnimationFrame(() => {
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto'
      }
    })
  }, [value, disabled, onSend, teamMode, selectedTeamId, selectedSkillId, goalMode])

  /** 键盘事件：Enter 发送，Shift+Enter 换行 */
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        handleSend()
      }
    },
    [handleSend],
  )

  /** 输入变化 */
  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      setValue(e.target.value)
      adjustHeight()
    },
    [adjustHeight],
  )

  // ─── 专家团下拉菜单 ────────────────────────────────
  const expertTeamMenuItems: MenuProps['items'] = [
    {
      key: 'auto',
      label: (
        <div className={styles.menuItemInner}>
          <span className={styles.menuItemLabel}>🧠 Auto (自动匹配)</span>
          <span className={styles.menuItemDesc}>根据消息内容自动选择合适的专家团</span>
        </div>
      ),
    },
    { type: 'divider' as const },
    ...expertTeams.map((team) => ({
      key: String(team.id),
      label: (
        <div className={styles.menuItemInner}>
          <span className={styles.menuItemLabel}><ExpertAvatar avatar={team.icon} size={18} style={{ display: 'inline-flex', marginRight: 6, verticalAlign: 'middle' }} />{team.teamName}</span>
          {team.description && (
            <span className={styles.menuItemDesc}>{team.description}</span>
          )}
        </div>
      ),
    })),
    { type: 'divider' as const },
    {
      key: 'clear',
      label: '关闭（不使用专家团）',
    },
  ]

  const handleExpertTeamSelect: NonNullable<MenuProps['onClick']> = (info) => {
    if (info.key === 'clear') {
      setTeamMode('off')
      setSelectedTeamId(null)
    } else if (info.key === 'auto') {
      setTeamMode('auto')
      setSelectedTeamId(null)
      setGoalMode(false) // 互斥：激活专家团时关闭 Goal
    } else {
      setTeamMode('manual')
      setSelectedTeamId(Number(info.key))
      setGoalMode(false) // 互斥：激活专家团时关闭 Goal
    }
  }

  // ─── 技能下拉菜单 ──────────────────────────────────
  const skillMenuItems: MenuProps['items'] = [
    ...skills.map((skill) => ({
      key: String(skill.id),
      label: (
        <div className={styles.menuItemInner}>
          <span className={styles.menuItemLabel}>⚡ {skill.displayName}</span>
          {skill.description && (
            <span className={styles.menuItemDesc}>{skill.description}</span>
          )}
        </div>
      ),
    })),
    { type: 'divider' as const },
    {
      key: 'clear',
      label: '默认（不指定技能）',
    },
  ]

  const handleSkillSelect: NonNullable<MenuProps['onClick']> = (info) => {
    if (info.key === 'clear') {
      setSelectedSkillId(null)
    } else {
      setSelectedSkillId(Number(info.key))
    }
  }

  // ─── 渲染 ──────────────────────────────────────────
  return (
    <div className={styles.inputContainer}>
      <div className={styles.inputBox}>
        {/* 多行输入区域 */}
        <textarea
          ref={textareaRef}
          className={styles.inputTextarea}
          value={value}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder={goalMode ? '描述你的目标… (如：帮我分析竞品，出一份市场报告)' : '输入消息… (Enter 发送，Shift+Enter 换行)' }
          disabled={disabled}
          rows={1}
          aria-label="消息输入框"
        />

        {/* 底部工具栏 */}
        <div className={styles.toolbar}>
          {/* 左侧选择器 */}
          <div className={styles.toolbarLeft}>
            {/* 专家团选择 */}
            <Dropdown
              menu={{ items: expertTeamMenuItems, onClick: handleExpertTeamSelect, selectedKeys: teamMode === 'auto' ? ['auto'] : selectedTeamId ? [String(selectedTeamId)] : [] }}
              trigger={['click']}
              placement="topLeft"
            >
              <button
                type="button"
                className={`${styles.toolButton} ${teamMode !== 'off' ? styles.toolButtonActive : ''}`}
              >
                <RobotOutlined />
                <span className={styles.toolButtonLabel}>
                  {selectedTeamName ?? '专家团'}
                </span>
                {teamMode !== 'off' && (
                  <span
                    className={styles.toolButtonClear}
                    role="button"
                    tabIndex={0}
                    onClick={(e) => { e.stopPropagation(); setTeamMode('off'); setSelectedTeamId(null) }}
                    onKeyDown={(e) => { if (e.key === 'Enter') { e.stopPropagation(); setTeamMode('off'); setSelectedTeamId(null) } }}
                  >
                    <CloseOutlined />
                  </span>
                )}
                <DownOutlined className={styles.toolButtonArrow} />
              </button>
            </Dropdown>

            {/* Goal 目标 */}
            <button
              type="button"
              className={`${styles.toolButton} ${goalMode ? styles.toolButtonActive : ''}`}
              onClick={() => {
                const next = !goalMode
                setGoalMode(next)
                // 激活 Goal 时关闭专家团
                if (next) {
                  setTeamMode('off')
                  setSelectedTeamId(null)
                }
                // 自动 focus 输入框
                if (next && !value.trim()) {
                  requestAnimationFrame(() => textareaRef.current?.focus())
                }
              }}
            >
              <AimOutlined />
              <span className={styles.toolButtonLabel}>
                {'目标'}
              </span>
              {goalMode && (
                <span
                  className={styles.toolButtonClear}
                  role="button"
                  tabIndex={0}
                  onClick={(e) => { e.stopPropagation(); setGoalMode(false) }}
                  onKeyDown={(e) => { if (e.key === 'Enter') { e.stopPropagation(); setGoalMode(false) } }}
                >
                  <CloseOutlined />
                </span>
              )}
            </button>

            {/* 技能选择 */}
            <Dropdown
              menu={{ items: skillMenuItems, onClick: handleSkillSelect, selectedKeys: selectedSkillId ? [String(selectedSkillId)] : [] }}
              trigger={['click']}
              placement="topLeft"
            >
              <button
                type="button"
                className={`${styles.toolButton} ${selectedSkillId != null ? styles.toolButtonActive : ''}`}
              >
                <ThunderboltOutlined />
                <span className={styles.toolButtonLabel}>
                  {selectedSkillName ?? '技能'}
                </span>
                {selectedSkillId != null && (
                  <span
                    className={styles.toolButtonClear}
                    role="button"
                    tabIndex={0}
                    onClick={(e) => { e.stopPropagation(); setSelectedSkillId(null) }}
                    onKeyDown={(e) => { if (e.key === 'Enter') { e.stopPropagation(); setSelectedSkillId(null) } }}
                  >
                    <CloseOutlined />
                  </span>
                )}
                <DownOutlined className={styles.toolButtonArrow} />
              </button>
            </Dropdown>
          </div>

          {/* 右侧发送 / 停止 */}
          <div className={styles.toolbarRight}>
            {isLoading && onStop ? (
              <Tooltip title="停止生成">
                <button
                  className={styles.stopButton}
                  onClick={onStop}
                  aria-label="停止生成"
                >
                  <StopOutlined />
                </button>
              </Tooltip>
            ) : (
              <Tooltip title="发送消息">
                <button
                  className={styles.sendButton}
                  onClick={handleSend}
                  disabled={!value.trim() || disabled}
                  aria-label="发送消息"
                >
                  <SendOutlined />
                </button>
              </Tooltip>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
