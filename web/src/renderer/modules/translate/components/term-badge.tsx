/**
 * 术语命中标记组件
 * 在译文中高亮显示命中的术语词汇
 */

import React from 'react'
import { Tooltip } from 'antd'
import styles from './translate-panel.module.css'
import type { TermHit } from '../types/translate'

interface TermBadgeProps {
  /** 术语命中列表 */
  termHits: TermHit[]
}

/**
 * 术语命中标记列表
 * 显示在译文下方，展示命中的术语及对应翻译
 */
export const TermBadgeList: React.FC<TermBadgeProps> = ({ termHits }) => {
  if (termHits.length === 0) return null

  return (
    <div className={styles.termBadges}>
      {termHits.map((hit, index) => (
        <Tooltip key={`${hit.term}-${index}`} title={`${hit.term} → ${hit.translation}`}>
          <span className={styles.termBadge}>
            <span className={styles.termBadgeIcon}>📚</span>
            {hit.term}
          </span>
        </Tooltip>
      ))}
    </div>
  )
}

interface TermHighlightTextProps {
  /** 译文内容 */
  text: string
  /** 术语命中列表 */
  termHits: TermHit[]
}

/**
 * 带术语高亮的译文渲染
 * 将命中术语在译文中用高亮样式标注
 */
export const TermHighlightText: React.FC<TermHighlightTextProps> = ({ text, termHits }) => {
  if (termHits.length === 0) {
    return <>{text}</>
  }

  // 构建替换映射（按长度降序，避免短术语误匹配长术语的一部分）
  const sortedTerms = [...termHits].sort((a, b) => b.translation.length - a.translation.length)

  // 构建正则（转义特殊字符）
  const escapedTerms = sortedTerms.map((t) => t.translation.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
  const regex = new RegExp(`(${escapedTerms.join('|')})`, 'g')

  const parts = text.split(regex)

  return (
    <>
      {parts.map((part, index) => {
        const matchedTerm = sortedTerms.find((t) => t.translation === part)
        if (matchedTerm) {
          return (
            <Tooltip key={index} title={`${matchedTerm.term}（术语）`}>
              <span className={styles.termHighlight}>{part}</span>
            </Tooltip>
          )
        }
        return <React.Fragment key={index}>{part}</React.Fragment>
      })}
    </>
  )
}
