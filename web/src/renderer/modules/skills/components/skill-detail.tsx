/** 技能详情组件（Drawer） */

import { Drawer, Tag, Divider } from 'antd'
import {
  ThunderboltOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  CalendarOutlined,
  LinkOutlined,
} from '@ant-design/icons'
import type { Skill } from '../types/skills'
import styles from './skills-panel.module.css'

interface SkillDetailProps {
  open: boolean
  skill: Skill | null
  onClose: () => void
  onRefine?: (skill: Skill) => void
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

${skill.triggerWords.map((w) => `- \`${w}\``).join('\n') || '无'}

## 使用示例

当用户提到相关触发词时，此技能会自动激活。

## 依赖

${skill.dependencies.length > 0 ? skill.dependencies.map((d) => `- ${d}`).join('\n') : '无外部依赖'}
`
}

/** 技能详情 Drawer */
export function SkillDetail({ open, skill, onClose, onRefine }: SkillDetailProps) {
  if (!skill) return null

  const skillMd = getMockSkillMd(skill)

  return (
    <Drawer title={`🔧 ${skill.name}`} open={open} onClose={onClose} width={500} destroyOnClose>
      <div className={styles.detailContent}>
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
              <div className={styles.statValue}>{skill.stats.callCount}</div>
              <div className={styles.statLabel}>
                <ThunderboltOutlined /> 调用次数
              </div>
            </div>
            <div className={styles.statCard}>
              <div className={styles.statValue}>{(skill.stats.successRate * 100).toFixed(0)}%</div>
              <div className={styles.statLabel}>
                <CheckCircleOutlined /> 成功率
              </div>
            </div>
            <div className={styles.statCard}>
              <div className={styles.statValue}>{formatDuration(skill.stats.avgDuration)}</div>
              <div className={styles.statLabel}>
                <ClockCircleOutlined /> 平均耗时
              </div>
            </div>
          </div>
        </div>

        {/* 依赖 */}
        {skill.dependencies.length > 0 && (
          <div className={styles.detailSection}>
            <span className={styles.detailLabel}>
              <LinkOutlined /> 依赖
            </span>
            <div className={styles.dependencies}>
              {skill.dependencies.map((dep) => (
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
            {skill.triggerWords.map((word) => (
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
      </div>
    </Drawer>
  )
}
