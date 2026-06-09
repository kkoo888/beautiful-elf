/** 长期记忆 Tab — MEMORY.md 编辑视图 */

import { useState, useEffect, useCallback } from 'react'
import { Typography, Button, Card, Spin, message, Space, Empty } from 'antd'
import { EditOutlined, SaveOutlined, BookOutlined } from '@ant-design/icons'
import { fetchLongTermMemory, updateLongTermMemory } from '../services/memory-api'
import type { MarkdownMemoryEntry } from '../services/memory-api'

const { Text } = Typography

export function LongTermTab() {
  const [memory, setMemory] = useState<MarkdownMemoryEntry | null>(null)
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState(false)
  const [editContent, setEditContent] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    fetchLongTermMemory()
      .then(setMemory)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const handleEdit = useCallback(() => {
    setEditContent(memory?.content ?? '')
    setEditing(true)
  }, [memory])

  const handleSave = useCallback(async () => {
    setSaving(true)
    try {
      const updated = await updateLongTermMemory(editContent)
      setMemory(updated)
      setEditing(false)
      message.success('长期记忆已保存')
    } catch {
      message.error('保存失败，请重试')
    } finally {
      setSaving(false)
    }
  }, [editContent])

  const handleCancel = useCallback(() => {
    setEditing(false)
    setEditContent('')
  }, [])

  if (loading) return <Spin style={{ display: 'block', marginTop: 80 }} />

  if (!memory) {
    return <Empty description="暂无长期记忆" image={Empty.PRESENTED_IMAGE_SIMPLE} />
  }

  return (
    <Card
      title={
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <BookOutlined style={{ color: '#722ed1' }} />
          <span>长期记忆</span>
          <Text type="secondary" style={{ fontSize: 12, fontWeight: 'normal' }}>
            {memory.wordCount} 字
          </Text>
        </div>
      }
      extra={
        editing ? (
          <Space>
            <Button size="small" onClick={handleCancel}>取消</Button>
            <Button
              size="small"
              type="primary"
              icon={<SaveOutlined />}
              loading={saving}
              onClick={handleSave}
            >
              保存
            </Button>
          </Space>
        ) : (
          <Button
            size="small"
            icon={<EditOutlined />}
            onClick={handleEdit}
          >
            编辑
          </Button>
        )
      }
      style={{ height: '100%', minHeight: 0 }}
      styles={{ body: { padding: '16px 24px', height: 'calc(100% - 56px)', overflowY: 'auto', minHeight: 0 } }}
    >
      {editing ? (
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
          <Text type="secondary" style={{ marginBottom: 8, fontSize: 12 }}>
            支持 Markdown 格式
          </Text>
          <textarea
            value={editContent}
            onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setEditContent(e.target.value)}
            style={{
              flex: 1,
              minHeight: 300,
              padding: 12,
              border: '1px solid #d9d9d9',
              borderRadius: 6,
              fontFamily: "'SFMono-Regular', Consolas, monospace",
              fontSize: 13,
              lineHeight: 1.7,
              resize: 'vertical',
            }}
          />
        </div>
      ) : (
        <div
          style={{ whiteSpace: 'pre-wrap', lineHeight: 1.8, fontSize: 14 }}
          dangerouslySetInnerHTML={{ __html: renderMarkdown(memory.content) }}
        />
      )}
    </Card>
  )
}

/** 简单 Markdown → HTML */
function renderMarkdown(md: string): string {
  return md
    .replace(/^### (.+)$/gm, '<h4 style="margin:16px 0 8px;color:#333;">$1</h4>')
    .replace(/^## (.+)$/gm, '<h3 style="margin:20px 0 10px;color:#722ed1;border-bottom:1px solid #f0f0f0;padding-bottom:6px;">$1</h3>')
    .replace(/^# (.+)$/gm, '<h2 style="margin:24px 0 12px;color:#000;">$1</h2>')
    .replace(/^> (.+)$/gm, '<blockquote style="border-left:3px solid #722ed1;padding-left:12px;color:#666;margin:12px 0;">$1</blockquote>')
    .replace(/^- (.+)$/gm, '<li style="margin:4px 0;margin-left:20px;">$1</li>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n{2,}/g, '</p><p style="margin:8px 0;">')
    .replace(/\n/g, '<br/>')
    .replace(/^/, '<p style="margin:8px 0;">')
    .replace(/$/, '</p>')
}
