/**
 * Prompt 版本 Diff 对比
 * 左右分栏展示两个版本内容，高亮差异行
 */

import { useCallback, useMemo, useState } from 'react'
import { Modal, Select, Typography } from 'antd'
import dayjs from 'dayjs'
import type { PromptVersion } from '../types/settings'

const { Text } = Typography

interface PromptDiffProps {
  /** 所有版本列表 */
  versions: PromptVersion[]
  /** 左侧版本 ID */
  leftId: string
  /** 右侧版本 ID */
  rightId: string
  /** 弹窗是否可见 */
  open: boolean
  /** 关闭回调 */
  onClose: () => void
}

/** 简易行级 diff：逐行比较，标记新增/删除/相同 */
type DiffLine = { type: 'same' | 'added' | 'removed'; text: string }

function computeLineDiff(
  oldText: string,
  newText: string
): { left: DiffLine[]; right: DiffLine[] } {
  const oldLines = oldText.split('\n')
  const newLines = newText.split('\n')

  // LCS-based diff (simplified Myers)
  const m = oldLines.length
  const n = newLines.length
  const dp: number[][] = Array.from({ length: m + 1 }, () => Array(n + 1).fill(0))

  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      dp[i][j] =
        oldLines[i - 1] === newLines[j - 1]
          ? dp[i - 1][j - 1] + 1
          : Math.max(dp[i - 1][j], dp[i][j - 1])
    }
  }

  const left: DiffLine[] = []
  const right: DiffLine[] = []
  let i = m
  let j = n

  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && oldLines[i - 1] === newLines[j - 1]) {
      left.unshift({ type: 'same', text: oldLines[i - 1] })
      right.unshift({ type: 'same', text: newLines[j - 1] })
      i--
      j--
    } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
      right.unshift({ type: 'added', text: newLines[j - 1] })
      left.unshift({ type: 'same', text: '' })
      j--
    } else {
      left.unshift({ type: 'removed', text: oldLines[i - 1] })
      right.unshift({ type: 'same', text: '' })
      i--
    }
  }

  return { left, right }
}

/** 行背景色映射 */
const LINE_STYLES: Record<DiffLine['type'], React.CSSProperties> = {
  same: {},
  added: { background: '#e6ffed' },
  removed: { background: '#ffeef0' },
}

const DARK_LINE_STYLES: Record<DiffLine['type'], React.CSSProperties> = {
  same: {},
  added: { background: '#1a3a2a' },
  removed: { background: '#3a1a1a' },
}

export function PromptDiff({ versions, leftId, rightId, open, onClose }: PromptDiffProps) {
  const [currentLeftId, setCurrentLeftId] = useState(leftId)
  const [currentRightId, setCurrentRightId] = useState(rightId)

  const leftVersion = versions.find((v) => v.id === currentLeftId)
  const rightVersion = versions.find((v) => v.id === currentRightId)

  const isDark =
    typeof document !== 'undefined' && document.documentElement.classList.contains('dark')
  const lineStyles = isDark ? DARK_LINE_STYLES : LINE_STYLES

  const diff = useMemo(() => {
    if (!leftVersion || !rightVersion) return { left: [], right: [] }
    return computeLineDiff(leftVersion.content, rightVersion.content)
  }, [leftVersion, rightVersion])

  const versionOptions = useMemo(
    () =>
      versions
        .slice()
        .sort((a, b) => a.version - b.version)
        .map((v) => ({
          value: v.id,
          label: `v${v.version} (${dayjs(v.createdAt).format('MM-DD HH:mm')})`,
        })),
    [versions]
  )

  const handleLeftChange = useCallback((val: string) => setCurrentLeftId(val), [])
  const handleRightChange = useCallback((val: string) => setCurrentRightId(val), [])

  return (
    <Modal title="版本对比" open={open} onCancel={onClose} footer={null} width={900} destroyOnHidden>
      <div style={{ display: 'flex', gap: 16, marginBottom: 16 }}>
        <div style={{ flex: 1 }}>
          <Text type="secondary" style={{ fontSize: 12, marginBottom: 4, display: 'block' }}>
            基准版本（旧）
          </Text>
          <Select
            value={currentLeftId}
            onChange={handleLeftChange}
            options={versionOptions}
            style={{ width: '100%' }}
          />
        </div>
        <div style={{ flex: 1 }}>
          <Text type="secondary" style={{ fontSize: 12, marginBottom: 4, display: 'block' }}>
            对比版本（新）
          </Text>
          <Select
            value={currentRightId}
            onChange={handleRightChange}
            options={versionOptions}
            style={{ width: '100%' }}
          />
        </div>
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: 1,
          background: '#e8e8e8',
          borderRadius: 8,
          overflow: 'hidden',
          maxHeight: 500,
          overflowY: 'auto',
        }}
      >
        {/* 左侧 */}
        <div style={{ background: isDark ? '#1f1f1f' : '#fff' }}>
          <div
            style={{
              padding: '6px 12px',
              background: isDark ? '#2a2a2a' : '#fafafa',
              borderBottom: '1px solid #e8e8e8',
              fontWeight: 600,
              fontSize: 13,
            }}
          >
            v{leftVersion?.version ?? '?'}
          </div>
          {diff.left.map((line, idx) => (
            <pre
              key={idx}
              style={{
                margin: 0,
                padding: '2px 12px',
                fontSize: 13,
                fontFamily: "'Cascadia Code', 'Fira Code', monospace",
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-all',
                minHeight: 20,
                ...lineStyles[line.type],
              }}
            >
              {line.text || '\u00A0'}
            </pre>
          ))}
        </div>

        {/* 右侧 */}
        <div style={{ background: isDark ? '#1f1f1f' : '#fff' }}>
          <div
            style={{
              padding: '6px 12px',
              background: isDark ? '#2a2a2a' : '#fafafa',
              borderBottom: '1px solid #e8e8e8',
              fontWeight: 600,
              fontSize: 13,
            }}
          >
            v{rightVersion?.version ?? '?'}
          </div>
          {diff.right.map((line, idx) => (
            <pre
              key={idx}
              style={{
                margin: 0,
                padding: '2px 12px',
                fontSize: 13,
                fontFamily: "'Cascadia Code', 'Fira Code', monospace",
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-all',
                minHeight: 20,
                ...lineStyles[line.type],
              }}
            >
              {line.text || '\u00A0'}
            </pre>
          ))}
        </div>
      </div>
    </Modal>
  )
}
