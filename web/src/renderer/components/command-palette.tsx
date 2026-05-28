import { useState, useEffect, useRef, useCallback } from 'react'
import { Modal, Input, List, Typography, Space, Tag } from 'antd'
import { SearchOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { useDebounce } from '@/hooks'
import { useCommandStore } from '@/stores/use-command-store'
import type { Command } from '@/types'

const { Text } = Typography

interface CommandPaletteProps {
  open: boolean
  onClose: () => void
}

/**
 * 命令面板组件
 * Ctrl+K 全局唤起，支持模块动态注册命令
 * 按精确匹配 > 前缀匹配 > 模糊匹配排序，同级按使用频率
 */
export function CommandPalette({ open, onClose }: CommandPaletteProps) {
  const [searchText, setSearchText] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)
  const navigate = useNavigate()
  const debouncedSearch = useDebounce(searchText, 100)
  const commands = useCommandStore((state) => state.commands)
  const recordUsage = useCommandStore((state) => state.recordUsage)

  // 过滤和排序命令
  const filteredCommands = useCallback(() => {
    if (!debouncedSearch) return commands.slice(0, 20)

    const query = debouncedSearch.toLowerCase()
    return commands
      .filter((cmd) => {
        const nameMatch = cmd.name.toLowerCase().includes(query)
        const keywordMatch = cmd.keywords.some((kw) => kw.toLowerCase().includes(query))
        return nameMatch || keywordMatch
      })
      .sort((a, b) => {
        // 精确匹配优先
        const aExact =
          a.name.toLowerCase() === query ||
          a.keywords.some((kw) => kw.toLowerCase() === query)
        const bExact =
          b.name.toLowerCase() === query ||
          b.keywords.some((kw) => kw.toLowerCase() === query)
        if (aExact && !bExact) return -1
        if (!aExact && bExact) return 1

        // 前缀匹配优先
        const aPrefix = a.name.toLowerCase().startsWith(query)
        const bPrefix = b.name.toLowerCase().startsWith(query)
        if (aPrefix && !bPrefix) return -1
        if (!aPrefix && bPrefix) return 1

        // 使用频率排序
        if (b.use_count !== a.use_count) return b.use_count - a.use_count

        // 最近使用时间排序
        return (b.last_used_at || 0) - (a.last_used_at || 0)
      })
      .slice(0, 20)
  }, [debouncedSearch, commands])

  const results = filteredCommands()

  // 执行命令
  const executeCommand = useCallback(
    (command: Command) => {
      recordUsage(command.id)
      command.action()
      onClose()
      setSearchText('')
      setSelectedIndex(0)
    },
    [recordUsage, onClose]
  )

  // 键盘导航
  useEffect(() => {
    if (!open) return

    const handleKeyDown = (e: KeyboardEvent) => {
      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault()
          setSelectedIndex((prev) => Math.min(prev + 1, results.length - 1))
          break
        case 'ArrowUp':
          e.preventDefault()
          setSelectedIndex((prev) => Math.max(prev - 1, 0))
          break
        case 'Enter':
          e.preventDefault()
          if (results[selectedIndex]) {
            executeCommand(results[selectedIndex])
          }
          break
        case 'Escape':
          e.preventDefault()
          onClose()
          break
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [open, results, selectedIndex, executeCommand, onClose])

  // 打开时聚焦输入框
  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 100)
      setSelectedIndex(0)
      setSearchText('')
    }
  }, [open])

  return (
    <Modal
      open={open}
      onCancel={onClose}
      footer={null}
      closable={false}
      width={600}
      styles={{ body: { padding: 0 } }}
      destroyOnClose
    >
      <Input
        ref={inputRef as React.RefObject<HTMLInputElement>}
        prefix={<SearchOutlined />}
        placeholder="输入命令..."
        value={searchText}
        onChange={(e) => {
          setSearchText(e.target.value)
          setSelectedIndex(0)
        }}
        size="large"
        style={{
          borderRadius: 0,
          border: 'none',
          borderBottom: '1px solid var(--ant-color-border)'
        }}
      />
      <List
        dataSource={results}
        style={{ maxHeight: 400, overflow: 'auto' }}
        renderItem={(command, index) => (
          <List.Item
            key={command.id}
            onClick={() => executeCommand(command)}
            style={{
              padding: '8px 16px',
              cursor: 'pointer',
              backgroundColor:
                index === selectedIndex ? 'var(--ant-color-bg-text-hover)' : undefined
            }}
          >
            <Space>
              <span style={{ fontSize: 18 }}>{command.icon}</span>
              <Text>{command.name}</Text>
              <Tag color="default" style={{ marginLeft: 8 }}>
                {command.module}
              </Tag>
            </Space>
          </List.Item>
        )}
      />
      {results.length === 0 && (
        <div style={{ padding: '24px', textAlign: 'center' }}>
          <Text type="secondary">未找到匹配的命令</Text>
        </div>
      )}
    </Modal>
  )
}
