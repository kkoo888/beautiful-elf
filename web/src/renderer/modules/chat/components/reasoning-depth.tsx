/**
 * 推理深度切换组件
 * Segmented 切换：快速 / 深度 / 全面
 */

import React, { useCallback } from 'react'
import styles from './chat-panel.module.css'
import type { ReasoningDepth } from '../types/chat'

/** 推理深度选项 */
const DEPTH_OPTIONS: { value: ReasoningDepth; label: string; description: string }[] = [
  { value: 'fast', label: '⚡ 快速', description: '快速回答，适合简单问题' },
  { value: 'deep', label: '🔍 深度', description: '深度思考，适合复杂问题' },
  { value: 'full', label: '🧠 全面', description: '全面分析，适合决策参考' }
]

interface ReasoningDepthSwitchProps {
  /** 当前选中的深度 */
  value: ReasoningDepth
  /** 切换回调 */
  onChange: (depth: ReasoningDepth) => void
}

export const ReasoningDepthSwitch: React.FC<ReasoningDepthSwitchProps> = ({
  value,
  onChange
}) => {
  const handleClick = useCallback(
    (depth: ReasoningDepth) => {
      if (depth !== value) {
        onChange(depth)
      }
    },
    [value, onChange]
  )

  return (
    <div className={styles.reasoningSwitch}>
      {DEPTH_OPTIONS.map(({ value: depth, label }) => (
        <button
          key={depth}
          className={`${styles.reasoningOption} ${
            value === depth ? styles.reasoningOptionActive : ''
          }`}
          onClick={() => handleClick(depth)}
          aria-pressed={value === depth}
          title={DEPTH_OPTIONS.find((d) => d.value === depth)?.description}
        >
          {label}
        </button>
      ))}
    </div>
  )
}
