/** AI 思考中动画指示器 */

import React from 'react'
import styles from './chat-panel.module.css'

interface ThinkingIndicatorProps {
  /** 是否显示 */
  visible: boolean
  /** 提示文字 */
  text?: string
}

export const ThinkingIndicator: React.FC<ThinkingIndicatorProps> = ({
  visible,
  text = '思考中'
}) => {
  if (!visible) return null

  return (
    <div className={styles.messageRow + ' ' + styles.messageRowAssistant}>
      <div className={styles.bubble + ' ' + styles.bubbleAssistant}>
        <div className={styles.thinkingIndicator}>
          <span className={styles.thinkingDot} />
          <span className={styles.thinkingDot} />
          <span className={styles.thinkingDot} />
          <span className={styles.thinkingText}>{text}</span>
        </div>
      </div>
    </div>
  )
}
