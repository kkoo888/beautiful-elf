/** 每日日志 Tab — Markdown 日记视图 */

import { useState, useEffect, useCallback } from 'react'
import { Typography, List, Card, Empty, Spin, Tag } from 'antd'
import { CalendarOutlined, FileTextOutlined } from '@ant-design/icons'
import { fetchDailyLogs, fetchMarkdownMemory } from '../services/memory-api'
import type { MarkdownMemoryEntry } from '../services/memory-api'

const { Text } = Typography

export function DailyLogTab() {
  const [logs, setLogs] = useState<MarkdownMemoryEntry[]>([])
  const [selected, setSelected] = useState<MarkdownMemoryEntry | null>(null)
  const [loading, setLoading] = useState(true)
  const [detailLoading, setDetailLoading] = useState(false)

  useEffect(() => {
    fetchDailyLogs(14)
      .then(items => { setLogs(items); if (items.length > 0) handleSelect(items[0]) })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const handleSelect = useCallback(async (item: MarkdownMemoryEntry) => {
    setDetailLoading(true)
    try {
      const detail = await fetchMarkdownMemory(item.id)
      setSelected(detail)
    } catch {
      setSelected({ ...item, content: '加载失败' })
    } finally {
      setDetailLoading(false)
    }
  }, [])

  if (loading) return <Spin style={{ display: 'block', marginTop: 80 }} />

  if (logs.length === 0) {
    return <Empty description="暂无每日日志" image={Empty.PRESENTED_IMAGE_SIMPLE} />
  }

  return (
    <div style={{ display: 'flex', gap: 16, height: '100%', minHeight: 400 }}>
      {/* 左侧：日期列表 */}
      <div style={{ width: 200, flexShrink: 0, overflowY: 'auto' }}>
        <List
          size="small"
          dataSource={logs}
          renderItem={item => (
            <List.Item
              style={{
                cursor: 'pointer',
                background: selected?.id === item.id ? '#e6f4ff' : 'transparent',
                borderRadius: 6,
                padding: '8px 12px',
                marginBottom: 4,
              }}
              onClick={() => handleSelect(item)}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <CalendarOutlined style={{ color: '#1677ff' }} />
                <div>
                  <Text strong style={{ fontSize: 13 }}>{item.title}</Text>
                  <br />
                  <Text type="secondary" style={{ fontSize: 11 }}>
                    {item.wordCount} 字
                  </Text>
                </div>
              </div>
            </List.Item>
          )}
        />
      </div>

      {/* 右侧：日志内容 */}
      <Card
        style={{ flex: 1, overflow: 'auto' }}
        styles={{ body: { padding: '16px 24px' } }}
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <FileTextOutlined />
            <span>{selected?.title ?? '选择日期'}</span>
            {selected && <Tag color="blue">{selected.wordCount} 字</Tag>}
          </div>
        }
      >
        {detailLoading ? (
          <Spin style={{ display: 'block', marginTop: 40 }} />
        ) : selected?.content ? (
          <div
            style={{ whiteSpace: 'pre-wrap', lineHeight: 1.8, fontSize: 14 }}
            dangerouslySetInnerHTML={{ __html: renderMarkdown(selected.content) }}
          />
        ) : (
          <Empty description="选择一天的日志查看" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        )}
      </Card>
    </div>
  )
}

/** 简单 Markdown → HTML（标题 + 段落 + 粗体） */
function renderMarkdown(md: string): string {
  return md
    .replace(/^### (.+)$/gm, '<h4 style="margin:16px 0 8px;color:#333;">$1</h4>')
    .replace(/^## (.+)$/gm, '<h3 style="margin:20px 0 10px;color:#1677ff;border-bottom:1px solid #f0f0f0;padding-bottom:6px;">$1</h3>')
    .replace(/^# (.+)$/gm, '<h2 style="margin:24px 0 12px;color:#000;">$1</h2>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n{2,}/g, '</p><p style="margin:8px 0;">')
    .replace(/\n/g, '<br/>')
    .replace(/^/, '<p style="margin:8px 0;">')
    .replace(/$/, '</p>')
}
