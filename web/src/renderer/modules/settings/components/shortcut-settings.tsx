/**
 * 快捷键设置组件
 * 快捷键映射列表 + 冲突检测
 */

import { useCallback, useState } from 'react'
import { Table, Tag, Typography, Button, Modal, Input } from 'antd'
import { EditOutlined, WarningOutlined } from '@ant-design/icons'
import type { ShortcutItem } from '../types/settings'
import styles from './settings-panel.module.css'

const { Text } = Typography

/** 默认快捷键列表 */
const DEFAULT_SHORTCUTS: ShortcutItem[] = [
  { action: 'toggleWindow', description: '显示/隐藏窗口', keys: 'Alt+Space', editable: true },
  { action: 'newChat', description: '新建对话', keys: 'Ctrl+N', editable: true },
  { action: 'search', description: '全局搜索', keys: 'Ctrl+K', editable: true },
  { action: 'settings', description: '打开设置', keys: 'Ctrl+,', editable: true },
  { action: 'quickSnippet', description: '快速片段', keys: 'Ctrl+Shift+S', editable: true },
  { action: 'clipboardHistory', description: '剪贴板历史', keys: 'Ctrl+Shift+V', editable: true },
  { action: 'send', description: '发送消息', keys: 'Enter', editable: false },
  { action: 'newLine', description: '换行', keys: 'Shift+Enter', editable: false },
]

/** 检测快捷键冲突 */
function findConflict(
  shortcuts: ShortcutItem[],
  newKeys: string,
  excludeAction: string
): string | null {
  const conflict = shortcuts.find((s) => s.action !== excludeAction && s.keys === newKeys)
  return conflict ? conflict.description : null
}

/** 渲染快捷键 */
function renderKeys(keys: string) {
  return (
    <span className={styles.shortcutKey}>
      {keys.split('+').map((k, i) => (
        <span key={i}>
          {i > 0 && <span style={{ margin: '0 2px' }}>+</span>}
          <kbd className={styles.kbd}>{k}</kbd>
        </span>
      ))}
    </span>
  )
}

export function ShortcutSettings() {
  const [shortcuts, setShortcuts] = useState<ShortcutItem[]>(DEFAULT_SHORTCUTS)
  const [editing, setEditing] = useState<ShortcutItem | null>(null)
  const [newKeys, setNewKeys] = useState('')
  const [conflict, setConflict] = useState<string | null>(null)

  const handleEdit = useCallback((item: ShortcutItem) => {
    setEditing(item)
    setNewKeys(item.keys)
    setConflict(null)
  }, [])

  const handleSave = useCallback(() => {
    if (!editing || !newKeys.trim()) return
    const c = findConflict(shortcuts, newKeys, editing.action)
    if (c) {
      setConflict(c)
      return
    }
    setShortcuts((prev) =>
      prev.map((s) => (s.action === editing.action ? { ...s, keys: newKeys.trim() } : s))
    )
    setEditing(null)
  }, [editing, newKeys, shortcuts])

  const columns = [
    {
      title: '功能',
      dataIndex: 'description',
      key: 'description',
    },
    {
      title: '快捷键',
      dataIndex: 'keys',
      key: 'keys',
      render: (keys: string) => renderKeys(keys),
    },
    {
      title: '',
      key: 'action',
      width: 60,
      render: (_: unknown, record: ShortcutItem) =>
        record.editable ? (
          <Button
            type="text"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          />
        ) : (
          <Tag color="default">固定</Tag>
        ),
    },
  ]

  return (
    <div>
      <Table
        dataSource={shortcuts}
        columns={columns}
        rowKey="action"
        pagination={false}
        size="small"
      />

      <Modal
        title="修改快捷键"
        open={!!editing}
        onOk={handleSave}
        onCancel={() => setEditing(null)}
        okText="保存"
        cancelText="取消"
      >
        <div style={{ marginBottom: 8 }}>
          <Text type="secondary">当前功能：{editing?.description}</Text>
        </div>
        <Input
          value={newKeys}
          onChange={(e) => {
            setNewKeys(e.target.value)
            setConflict(null)
          }}
          placeholder="按下新的快捷键组合"
          style={{ marginBottom: 8 }}
        />
        {conflict && (
          <div className={styles.conflictHint}>
            <WarningOutlined /> 与「{conflict}」冲突，请更换
          </div>
        )}
      </Modal>
    </div>
  )
}
