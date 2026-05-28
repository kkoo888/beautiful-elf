/** 快捷键捕获组件 */

import { useState, useEffect, useCallback } from 'react'
import { Tag, Space } from 'antd'

interface HotkeyCaptureProps {
  value: string
  onChange: (shortcut: string) => void
}

/** 修饰键映射 */
const MODIFIER_MAP: Record<string, string> = {
  Control: 'Ctrl',
  Meta: '⌘',
  Shift: 'Shift',
  Alt: 'Alt',
}

/** 按键映射 */
const KEY_MAP: Record<string, string> = {
  ',': ',',
  '.': '.',
  '/': '/',
  ';': ';',
  "'": "'",
  '[': '[',
  ']': ']',
  '\\': '\\',
  '-': '-',
  '=': '=',
  '`': '`',
  ' ': 'Space',
}

export function HotkeyCapture({ value, onChange }: HotkeyCaptureProps) {
  const [capturing, setCapturing] = useState(false)
  const [pressedKeys, setPressedKeys] = useState<string[]>([])

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      e.preventDefault()
      e.stopPropagation()

      const keys: string[] = []

      // 修饰键
      if (e.ctrlKey) keys.push('Ctrl')
      if (e.metaKey) keys.push('⌘')
      if (e.shiftKey) keys.push('Shift')
      if (e.altKey) keys.push('Alt')

      // 非修饰键
      const key = e.key
      if (!['Control', 'Meta', 'Shift', 'Alt'].includes(key)) {
        const displayKey = KEY_MAP[key] || key.toUpperCase()
        keys.push(displayKey)
      }

      setPressedKeys(keys)

      // 至少有一个修饰键 + 一个普通键才完成捕获
      const hasModifier = keys.some((k) => ['Ctrl', '⌘', 'Shift', 'Alt'].includes(k))
      const hasKey = keys.some((k) => !['Ctrl', '⌘', 'Shift', 'Alt'].includes(k))
      if (hasModifier && hasKey) {
        onChange(keys.join('+'))
        setCapturing(false)
      }
    },
    [onChange]
  )

  useEffect(() => {
    if (capturing) {
      window.addEventListener('keydown', handleKeyDown)
      return () => window.removeEventListener('keydown', handleKeyDown)
    }
  }, [capturing, handleKeyDown])

  const displayKeys = capturing ? pressedKeys : value.split('+')

  return (
    <div
      onClick={() => {
        setCapturing(true)
        setPressedKeys([])
      }}
      style={{
        cursor: 'pointer',
        padding: '4px 8px',
        borderRadius: 6,
        border: capturing ? '2px solid var(--color-primary)' : '1px solid var(--color-border)',
        background: capturing ? 'var(--color-primary-bg)' : 'transparent',
        minWidth: 120,
        textAlign: 'center',
        transition: 'all 0.15s',
      }}
    >
      {capturing ? (
        pressedKeys.length > 0 ? (
          <Space size={2}>
            {pressedKeys.map((k, i) => (
              <Tag key={i} color="blue">{k}</Tag>
            ))}
          </Space>
        ) : (
          <span style={{ color: 'var(--color-text-secondary)' }}>请按下快捷键...</span>
        )
      ) : (
        <Space size={2}>
          {displayKeys.map((k, i) => (
            <Tag key={i}>{k}</Tag>
          ))}
        </Space>
      )}
    </div>
  )
}
