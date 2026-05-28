/** 快速回答标识组件 */

import React from 'react'
import styles from './chat-panel.module.css'

interface QuickAnswerBadgeProps {
  /** 是否显示 */
  visible: boolean
}

export const QuickAnswerBadge: React.FC<QuickAnswerBadgeProps> = ({ visible }) => {
  if (!visible) return null

  return (
    <span className={styles.quickBadge}>
      <span className={styles.quickBadgeIcon}>⚡</span>
      快速回答
    </span>
  )
}
