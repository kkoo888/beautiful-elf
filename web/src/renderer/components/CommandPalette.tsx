import { useState, useEffect, useRef, useCallback } from 'react'
import { Modal, Input, List, Typography, Space, Tag } from 'antd'
import {
  MessageOutlined,
  CalendarOutlined,
  CopyOutlined,
  CodeOutlined,
  BookOutlined,
  BrainOutlined,
  TranslationOutlined,
  ToolOutlined,
  BranchesOutlined,
  RobotOutlined,
  DashboardOutlined,
  SettingOutlined,
  BellOutlined,
  PawPrintOutlined,
  SearchOutlined
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { useDebounce } from '@/hooks'
import type { Command } from '@/types'

const { Text } = Typography

// 内置命令
const builtinCommands: Command[] = [
  { id: 'chat', name: '对话', keywords: ['chat', '对话', '聊天'], icon: '💬', module: 'core', action: () => {}, use_count: 0 },
  { id: 'schedule', name: '日程', keywords: ['schedule', '日程', '日历'], icon: '📅', module: 'core', action: () => {}, use_count: 0 },
  { id: 'clipboard', name: '剪贴板', keywords: ['clipboard', '剪贴板', '复制'], icon: '📋', module: 'core', action: () => {}, use_count: 0 },
  { id: 'snippets', name: '代码片段', keywords: ['snippets', '代码', '片段'], icon: '💻', module: 'core', action: () => {}, use_count: 0 },
  { id: 'knowledge', name: '知识库', keywords: ['knowledge', '知识', '文档'], icon: '📚', module: 'knowledge', action: () => {}, use_count: 0 },
  { id: 'memory', name: '记忆', keywords: ['memory', '记忆', '长期记忆'], icon: '🧠', module: 'knowledge', action: () => {}, use_count: 0 },
  { id: 'translate', name: '翻译', keywords: ['translate', '翻译'], icon: '🌐', module: 'knowledge', action: () => {}, use_count: 0 },
  { id: 'skills', name: '技能', keywords: ['skills', '技能', '插件'], icon: '🔧', module: 'knowledge', action: () => {}, use_count: 0 },
  { id: 'workflow', name: '工作流', keywords: ['workflow', '工作流', '流程'], icon: '⚙️', module: 'automation', action: () => {}, use_count: 0 },
  { id: 'subagent', name: '子代理', keywords: ['subagent', '子代理', '代理'], icon: '🤖', module: 'automation', action: () => {}, use_count: 0 },
  { id: 'tools', name: '工具管理', keywords: ['tools', '工具', '管理'], icon: '🔌', module: 'automation', action: () => {}, use_count: 0 },
  { id: 'pet', name: '宠物', keywords: ['pet', '宠物', '桌面宠物'], icon: '🐾', module: 'system', action: () => {}, use_count: 0 },
  { id: 'performance', name: '性能监控', keywords: ['performance', '性能', '监控'], icon: '📊', module: 'system', action: () => {}, use_count: 0 },
  { id: 'notification', name: '通知', keywords: ['notification', '通知', '消息'], icon: '🔔', module: 'system', action: () => {}, use_count: 0 },
  { id: 'settings', name: '设置', keywords: ['settings', '设置', '配置'], icon: '⚙️', module: 'system', action: () => {}, use_count: 0 }
]

interface CommandPaletteProps {
  open: boolean
  onClose: () => void
}

export function CommandPalette({ open, onClose }: CommandPaletteProps) {
  const [searchText, setSearchText] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)
  const navigate = useNavigate()
  const debouncedSearch = useDebounce(searchText, 100)

  // 过滤和排序命令
  const filteredCommands = useCallback(() => {
    if (!debouncedSearch) return builtinCommands

    const query = debouncedSearch.toLowerCase()
    return builtinCommands
      .filter((cmd) => {
        const nameMatch = cmd.name.toLowerCase().includes(query)
        const keywordMatch = cmd.keywords.some((kw) => kw.toLowerCase().includes(query))
        return nameMatch || keywordMatch
      })
      .sort((a, b) => {
        // 精确匹配优先
        const aExact = a.name.toLowerCase() === query || a.keywords.some((kw) => kw.toLowerCase() === query)
        const bExact = b.name.toLowerCase() === query || b.keywords.some((kw) => kw.toLowerCase() === query)
        if (aExact && !bExact) return -1
        if (!aExact && bExact) return 1

        // 前缀匹配优先
        const aPrefix = a.name.toLowerCase().startsWith(query)
        const bPrefix = b.name.toLowerCase().startsWith(query)
        if (aPrefix && !bPrefix) return -1
        if (!aPrefix && bPrefix) return 1

        // 使用频率排序
        return b.use_count - a.use_count
      })
      .slice(0, 20)
  }, [debouncedSearch])

  const commands = filteredCommands()

  // 执行命令
  const executeCommand = useCallback(
    (command: Command) => {
      navigate(`/${command.id === 'chat' ? '' : command.id}`)
      onClose()
      setSearchText('')
      setSelectedIndex(0)
    },
    [navigate, onClose]
  )

  // 键盘导航
  useEffect(() => {
    if (!open) return

    const handleKeyDown = (e: KeyboardEvent) => {
      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault()
          setSelectedIndex((prev) => Math.min(prev + 1, commands.length - 1))
          break
        case 'ArrowUp':
          e.preventDefault()
          setSelectedIndex((prev) => Math.max(prev - 1, 0))
          break
        case 'Enter':
          e.preventDefault()
          if (commands[selectedIndex]) {
            executeCommand(commands[selectedIndex])
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
  }, [open, commands, selectedIndex, executeCommand, onClose])

  // 打开时聚焦输入框
  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 100)
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
        style={{ borderRadius: 0, border: 'none', borderBottom: '1px solid var(--ant-color-border)' }}
      />
      <List
        dataSource={commands}
        style={{ maxHeight: 400, overflow: 'auto' }}
        renderItem={(command, index) => (
          <List.Item
            key={command.id}
            onClick={() => executeCommand(command)}
            style={{
              padding: '8px 16px',
              cursor: 'pointer',
              backgroundColor: index === selectedIndex ? 'var(--ant-color-bg-text-hover)' : undefined
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
      {commands.length === 0 && (
        <div style={{ padding: '24px', textAlign: 'center' }}>
          <Text type="secondary">未找到匹配的命令</Text>
        </div>
      )}
    </Modal>
  )
}
