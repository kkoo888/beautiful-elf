/** 快捷键设置面板 */

import { useState, useCallback } from 'react'
import { Table, Button, Tag, message, Popconfirm, Space } from 'antd'
import { EditOutlined, UndoOutlined } from '@ant-design/icons'
import { useHotkeys } from '../hooks/use-hotkeys'
import { HotkeyCapture } from './hotkey-capture'
import type { HotkeyConfig } from '../types/system'

export function HotkeySettings() {
  const { hotkeys, isLoading, checkConflict, updateHotkeyShortcut, resetToDefault, isMutating } =
    useHotkeys()

  const [editingId, setEditingId] = useState<string | null>(null)

  const handleSave = useCallback(
    async (id: string, shortcut: string) => {
      const conflict = checkConflict(shortcut, id)
      if (conflict) {
        void message.warning(`快捷键 ${shortcut} 已被「${conflict.name}」使用`)
        return
      }
      try {
        await updateHotkeyShortcut(id, shortcut)
        setEditingId(null)
        void message.success('快捷键已更新')
      } catch {
        // conflict error already shown in updateHotkeyShortcut
      }
    },
    [checkConflict, updateHotkeyShortcut]
  )

  const handleReset = useCallback(async () => {
    try {
      await resetToDefault()
      void message.success('已重置为默认快捷键')
    } catch {
      void message.error('重置失败')
    }
  }, [resetToDefault])

  const columns = [
    {
      title: '功能',
      dataIndex: 'name',
      key: 'name',
      width: 200,
    },
    {
      title: '所属模块',
      dataIndex: 'module',
      key: 'module',
      width: 120,
      render: (mod: string) => <Tag>{mod}</Tag>,
    },
    {
      title: '快捷键',
      dataIndex: 'shortcut',
      key: 'shortcut',
      width: 200,
      render: (_: string, record: HotkeyConfig) =>
        editingId === record.id ? (
          <HotkeyCapture
            value={record.shortcut}
            onChange={(shortcut) => void handleSave(record.id, shortcut)}
          />
        ) : (
          <Space size={2}>
            {record.shortcut.split('+').map((k, i) => (
              <Tag key={i}>{k}</Tag>
            ))}
          </Space>
        ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 100,
      render: (_: unknown, record: HotkeyConfig) => (
        <Button
          type="link"
          size="small"
          icon={<EditOutlined />}
          onClick={() => setEditingId(editingId === record.id ? null : record.id)}
          loading={isMutating}
        >
          {editingId === record.id ? '取消' : '编辑'}
        </Button>
      ),
    },
  ]

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'flex-end' }}>
        <Popconfirm title="确定重置为默认快捷键？" onConfirm={() => void handleReset}>
          <Button icon={<UndoOutlined />} size="small">
            重置默认
          </Button>
        </Popconfirm>
      </div>
      <Table
        dataSource={hotkeys}
        columns={columns}
        rowKey="id"
        loading={isLoading}
        pagination={false}
        size="small"
      />
    </div>
  )
}
