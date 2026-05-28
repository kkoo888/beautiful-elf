/** 技能卡片组件 */

import { Card, Switch, Tag, Tooltip } from 'antd'
import {
  ThunderboltOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons'
import type { Skill } from '../types/skills'
import styles from './skills-panel.module.css'

interface SkillCardProps {
  skill: Skill
  onToggle: (id: string, enabled: boolean) => void
  onClick: (skill: Skill) => void
  isToggling?: boolean
}

/** 格式化耗时 */
function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

/** 技能卡片 */
export function SkillCard({ skill, onToggle, onClick, isToggling }: SkillCardProps) {
  const handleToggle = (checked: boolean, e: React.MouseEvent) => {
    e.stopPropagation()
    onToggle(skill.id, checked)
  }

  return (
    <Card
      className={styles.card}
      hoverable
      onClick={() => onClick(skill)}
    >
      <div className={styles.cardBody}>
        {/* 头部：名称 + 开关 */}
        <div className={styles.cardHeader}>
          <div className={styles.cardInfo}>
            <span className={styles.cardName}>{skill.name}</span>
            <span className={styles.cardVersion}>v{skill.version}</span>
          </div>
          <Switch
            checked={skill.enabled}
            onChange={handleToggle}
            loading={isToggling}
            size="small"
          />
        </div>

        {/* 描述 */}
        <p className={styles.cardDesc}>{skill.description}</p>

        {/* 统计指标 */}
        <div className={styles.cardMeta}>
          <Tooltip title="调用次数">
            <span className={styles.metaItem}>
              <ThunderboltOutlined className={styles.metaIcon} />
              {skill.stats.callCount}
            </span>
          </Tooltip>
          <Tooltip title="成功率">
            <span className={styles.metaItem}>
              <CheckCircleOutlined className={styles.metaIcon} />
              {(skill.stats.successRate * 100).toFixed(0)}%
            </span>
          </Tooltip>
          <Tooltip title="平均耗时">
            <span className={styles.metaItem}>
              <ClockCircleOutlined className={styles.metaIcon} />
              {formatDuration(skill.stats.avgDuration)}
            </span>
          </Tooltip>
        </div>

        {/* 触发词标签 */}
        {skill.triggerWords.length > 0 && (
          <div className={styles.cardTags}>
            {skill.triggerWords.slice(0, 4).map((word) => (
              <Tag key={word} className={styles.tag} color="orange">
                {word}
              </Tag>
            ))}
            {skill.triggerWords.length > 4 && (
              <Tag className={styles.tag}>+{skill.triggerWords.length - 4}</Tag>
            )}
          </div>
        )}
      </div>
    </Card>
  )
}
