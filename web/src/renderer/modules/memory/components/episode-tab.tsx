/** 经历 Tab — 对话分组管理

功能:
  - 列表展示经历（按时间排序）
  - 按实体/时间范围筛选
  - 手动创建经历弹窗
  - 经历详情查看
*/

import { useState, useEffect, useCallback } from 'react'
import {
  Typography, Button, Space, Empty, Spin, Tag, App, DatePicker, Select, Input,
  Modal, Form,
} from 'antd'
import {
  PlusOutlined, SearchOutlined,
} from '@ant-design/icons'
import type { Dayjs } from 'dayjs'
import type { MemoryEpisode } from '../types/memory'
import {
  listEpisodes, createEpisode, searchEpisodes,
} from '../services/memory-entity-api'

const { Text, Title } = Typography
const { RangePicker } = DatePicker

export function EpisodeTab() {
  const { message } = App.useApp()
  const [episodes, setEpisodes] = useState<MemoryEpisode[]>([])
  const [loading, setLoading] = useState(true)
  const [searching, setSearching] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [entityFilter, setEntityFilter] = useState<number | undefined>()
  const [timeRange, setTimeRange] = useState<[Dayjs, Dayjs] | null>(null)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showDetailModal, setShowDetailModal] = useState(false)
  const [selectedEpisode, setSelectedEpisode] = useState<MemoryEpisode | null>(null)

  // 加载经历列表
  const loadEpisodes = useCallback(async () => {
    setLoading(true)
    try {
      const params: any = {}
      if (entityFilter) params.entity_id = entityFilter
      if (timeRange) {
        params.start_time = timeRange[0].format('YYYY-MM-DD')
        params.end_time = timeRange[1].format('YYYY-MM-DD')
      }

      const data = await listEpisodes(params)
      setEpisodes(data)
    } catch {
      message.error('加载经历失败')
    } finally {
      setLoading(false)
    }
  }, [entityFilter, timeRange, message])

  // 搜索经历
  const handleSearch = useCallback(async () => {
    if (!searchQuery.trim()) {
      loadEpisodes()
      return
    }

    setSearching(true)
    try {
      const data = await searchEpisodes(searchQuery)
      setEpisodes(data)
    } catch {
      message.error('搜索失败')
    } finally {
      setSearching(false)
    }
  }, [searchQuery, loadEpisodes, message])

  // 显示详情
  const handleShowDetail = (episode: MemoryEpisode) => {
    setSelectedEpisode(episode)
    setShowDetailModal(true)
  }

  // 创建经历
  const handleCreate = async (values: any) => {
    try {
      await createEpisode({
        conversation_id: values.conversationId,
        title: values.title,
        summary: values.summary,
      })
      message.success('创建成功')
      setShowCreateModal(false)
      loadEpisodes()
    } catch {
      message.error('创建失败')
    }
  }

  useEffect(() => {
    loadEpisodes()
  }, [loadEpisodes])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: 12 }}>
      {/* 工具栏 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexShrink: 0 }}>
        <Space size={8}>
          <Input
            placeholder="搜索经历..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onPressEnter={handleSearch}
            suffix={<SearchOutlined />}
            style={{ width: 200 }}
          />
          <Select
            placeholder="按实体筛选"
            value={entityFilter}
            onChange={(value) => setEntityFilter(value)}
            allowClear
            style={{ width: 120 }}
            options={[
              { label: '实体 1', value: 1 },
              { label: '实体 2', value: 2 },
              { label: '实体 3', value: 3 },
            ]}
          />
          <RangePicker
            value={timeRange}
            onChange={(dates) => setTimeRange(dates as [Dayjs, Dayjs])}
            style={{ width: 240 }}
          />
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setShowCreateModal(true)}
          >
            创建经历
          </Button>
        </Space>
        <Space size={8}>
          <Button onClick={loadEpisodes}>刷新</Button>
          <Button onClick={handleSearch} loading={searching}>
            搜索
          </Button>
        </Space>
      </div>

      {/* 列表 */}
      <div style={{ flex: 1, overflow: 'auto', minHeight: 0 }}>
        {loading ? (
          <div style={{ display: 'flex', justifyContent: 'center', paddingTop: 60 }}>
            <Spin />
          </div>
        ) : episodes.length === 0 ? (
          <Empty
            description="暂无经历，点击「创建经历」开始"
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          />
        ) : (
          <div>
            {episodes.map((ep) => (
              <div
                key={ep.id}
                style={{
                  padding: '12px 0',
                  borderBottom: '1px solid #f0f0f0',
                  cursor: 'pointer',
                }}
                onClick={() => handleShowDetail(ep)}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Space size={8}>
                    <Tag color="blue">#{ep.id}</Tag>
                    <Text strong>{ep.title}</Text>
                  </Space>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {ep.startedAt} — {ep.endedAt}
                  </Text>
                </div>
                {ep.summary && (
                  <div style={{ marginTop: 4, fontSize: 12, color: '#8c8c8c', lineHeight: 1.6 }}>
                    {ep.summary.length > 100 ? ep.summary.slice(0, 100) + '...' : ep.summary}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 创建弹窗 */}
      <Modal
        title="创建经历"
        open={showCreateModal}
        onCancel={() => setShowCreateModal(false)}
        footer={null}
      >
        <Form onFinish={handleCreate}>
          <Form.Item
            name="conversationId"
            label="会话 ID"
            rules={[{ required: true, message: '请输入会话 ID' }]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            name="title"
            label="标题"
            rules={[{ required: true, message: '请输入标题' }]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            name="summary"
            label="摘要"
            rules={[{ required: true, message: '请输入摘要' }]}
          >
            <Input.TextArea rows={4} />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">创建</Button>
              <Button onClick={() => setShowCreateModal(false)}>取消</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* 详情弹窗 */}
      <Modal
        title="经历详情"
        open={showDetailModal}
        onCancel={() => setShowDetailModal(false)}
        footer={null}
        width={600}
      >
        {selectedEpisode && (
          <div>
            <div style={{ marginBottom: 16 }}>
              <Title level={4}>{selectedEpisode.title}</Title>
              <Text type="secondary">
                时间范围: {selectedEpisode.startedAt} 至 {selectedEpisode.endedAt}
              </Text>
            </div>
            <div style={{ marginBottom: 16 }}>
              <Text strong>摘要:</Text>
              <div style={{ marginTop: 8, whiteSpace: 'pre-wrap' }}>
                {selectedEpisode.summary}
              </div>
            </div>
            <div style={{ marginBottom: 16 }}>
              <Text strong>关联实体:</Text>
              <div style={{ marginTop: 8 }}>
                {(selectedEpisode.entityIds || '').split(',').filter(Boolean).map((id, idx) => (
                  <Tag key={idx} color="blue" style={{ marginRight: 8 }}>
                    {id}
                  </Tag>
                ))}
              </div>
            </div>
            <div style={{ marginBottom: 16 }}>
              <Text strong>关联观察:</Text>
              <div style={{ marginTop: 8 }}>
                <Text code>{selectedEpisode.observationIds}</Text>
              </div>
            </div>
            <div>
              <Text strong>创建时间:</Text>
              <Text type="secondary" style={{ marginLeft: 8 }}>
                {selectedEpisode.createdAt}
              </Text>
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}
