/** Insight History Tab — 洞察演化历史

功能:
  - 显示 Insight 演化历史
  - 置信度变化可视化（Progress 组件）
  - 仲裁记录展示
  - 手动触发冲突仲裁
*/

import { useState, useEffect, useCallback } from 'react'
import {
  Typography, Button, Space, Empty, Spin, Tag, App, Progress, Table, Modal, Form,
  Select, Input,
} from 'antd'
import {
  SearchOutlined, HistoryOutlined,
} from '@ant-design/icons'
import type { MemoryInsightHistory } from '../types/memory'
import type { MemoryInsight } from '../services/memory-entity-api'
import {
  listInsights, getInsightHistory, getConflicts, arbitrateInsight,
} from '../services/memory-entity-api'

const { Text, Title } = Typography

export function InsightHistoryTab() {
  const { message } = App.useApp()
  const [insights, setInsights] = useState<MemoryInsight[]>([])
  const [loading, setLoading] = useState(true)
  const [searching, setSearching] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [showHistoryModal, setShowHistoryModal] = useState(false)
  const [showArbitrationModal, setShowArbitrationModal] = useState(false)
  const [selectedInsight, setSelectedInsight] = useState<MemoryInsight | null>(null)
  const [selectedHistory, setSelectedHistory] = useState<MemoryInsightHistory[]>([])
  const [arbitrationData, setArbitrationData] = useState({ insightId: 0, importance: 5 })

  // 表格列定义
  const columns = [
    {
      title: '内容',
      dataIndex: 'content',
      key: 'content',
      render: (text: string) => <Text>{text}</Text>,
    },
    {
      title: '类型',
      dataIndex: 'insightType',
      key: 'insightType',
      render: (type: string) => {
        const typeMap = {
          pattern: { icon: <HistoryOutlined />, label: '模式', color: 'blue' },
          trend: { icon: <HistoryOutlined />, label: '趋势', color: 'cyan' },
          risk: { icon: <HistoryOutlined />, label: '风险', color: 'red' },
          insight: { icon: <HistoryOutlined />, label: '洞察', color: 'orange' },
        }
        const info = typeMap[type as keyof typeof typeMap] || typeMap.insight
        return (
          <Tag color={info.color} icon={info.icon}>
            {info.label}
          </Tag>
        )
      },
    },
    {
      title: '置信度',
      dataIndex: 'confidence',
      key: 'confidence',
      render: (confidence: number) => (
        <Progress
          percent={confidence}
          size="small"
          strokeColor={confidence > 70 ? '#52c41a' : confidence > 40 ? '#faad14' : '#ff4d4f'}
          format={() => `${confidence}%`}
        />
      ),
    },
    {
      title: '证据数',
      dataIndex: 'evidenceCount',
      key: 'evidenceCount',
    },
    {
      title: '操作',
      key: 'action',
      render: (text: string, record: MemoryInsight) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            onClick={() => handleShowHistory(record)}
          >
            历史
          </Button>
          <Button
            type="link"
            size="small"
            onClick={() => handleShowArbitration(record)}
          >
            仲裁
          </Button>
        </Space>
      ),
    },
  ]

  // 加载洞察列表
  const loadInsights = useCallback(async () => {
    setLoading(true)
    try {
      const { items } = await listInsights({ pageSize: 100 })
      setInsights(items)
    } catch (error) {
      message.error('加载洞察失败')
    } finally {
      setLoading(false)
    }
  }, [])

  // 显示历史
  const handleShowHistory = async (insight: MemoryInsight) => {
    try {
      const data = await getInsightHistory(insight.id)
      setSelectedHistory(data)
      setShowHistoryModal(true)
    } catch (error) {
      message.error('获取历史失败')
    }
  }

  // 显示仲裁
  const handleShowArbitration = (insight: MemoryInsight) => {
    setArbitrationData({ insightId: insight.id, importance: 5 })
    setShowArbitrationModal(true)
  }

  // 执行仲裁
  const handleArbitrate = async () => {
    try {
      const data = await arbitrateInsight(arbitrationData.insightId, {
        importance: arbitrationData.importance,
      })
      message.success('仲裁完成')
      setShowArbitrationModal(false)
      loadInsights()
    } catch (error) {
      message.error('仲裁失败')
    }
  }

  // 获取冲突
  const handleGetConflicts = async () => {
    try {
      const data = await getConflicts()
      setInsights(data)
      message.success(`找到 ${data.length} 个冲突洞察`)
    } catch (error) {
      message.error('获取冲突失败')
    }
  }

  useEffect(() => {
    loadInsights()
  }, [loadInsights])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: 12 }}>
      {/* 工具栏 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexShrink: 0 }}>
        <Space size={8}>
          <Input
            placeholder="搜索洞察..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onPressEnter={() => {}}
            suffix={<SearchOutlined />}
            style={{ width: 200 }}
          />
          <Button
            type="primary"
            icon={<HistoryOutlined />}
            onClick={handleGetConflicts}
          >
            查找冲突
          </Button>
        </Space>
        <Space size={8}>
          <Button onClick={loadInsights}>刷新</Button>
        </Space>
      </div>

      {/* 列表 */}
      <div style={{ flex: 1, overflow: 'auto', minHeight: 0 }}>
        {loading ? (
          <div style={{ display: 'flex', justifyContent: 'center', paddingTop: 60 }}>
            <Spin />
          </div>
        ) : insights.length === 0 ? (
          <Empty
            description="暂无洞察，点击「查找冲突」查看"
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          />
        ) : (
          <Table
            columns={columns}
            dataSource={insights}
            rowKey="id"
            pagination={{ pageSize: 20 }}
          />
        )}
      </div>

      {/* 历史弹窗 */}
      <Modal
        title="洞察演化历史"
        open={showHistoryModal}
        onCancel={() => setShowHistoryModal(false)}
        footer={null}
        width={600}
      >
        {selectedHistory.length > 0 ? (
          <div>
            <Table
              columns={[
                {
                  title: '操作类型',
                  dataIndex: 'action',
                  key: 'action',
                  render: (action: string) => (
                    <Tag color={action === 'created' ? 'green' : action === 'superseded' ? 'red' : 'blue'}>
                      {action}
                    </Tag>
                  ),
                },
                {
                  title: '旧置信度',
                  dataIndex: 'oldConfidence',
                  key: 'oldConfidence',
                  render: (confidence: number) => (
                    <Progress
                      percent={confidence}
                      size="small"
                      strokeColor="#ff4d4f"
                      format={() => `${confidence}%`}
                    />
                  ),
                },
                {
                  title: '新置信度',
                  dataIndex: 'newConfidence',
                  key: 'newConfidence',
                  render: (confidence: number) => (
                    <Progress
                      percent={confidence}
                      size="small"
                      strokeColor="#52c41a"
                      format={() => `${confidence}%`}
                    />
                  ),
                },
                {
                  title: '原因',
                  dataIndex: 'reason',
                  key: 'reason',
                },
                {
                  title: '时间',
                  dataIndex: 'createdAt',
                  key: 'createdAt',
                },
              ]}
              dataSource={selectedHistory}
              rowKey="id"
              pagination={{ pageSize: 10 }}
            />
          </div>
        ) : (
          <Empty description="暂无历史记录" />
        )}
      </Modal>

      {/* 仲裁弹窗 */}
      <Modal
        title="手动触发仲裁"
        open={showArbitrationModal}
        onCancel={() => setShowArbitrationModal(false)}
        footer={null}
      >
        {selectedInsight && (
          <div>
            <div style={{ marginBottom: 16 }}>
              <Title level={4}>{selectedInsight.content}</Title>
              <Text type="secondary">
                当前置信度: {selectedInsight.confidence}%
              </Text>
            </div>
            <Form onFinish={handleArbitrate}>
              <Form.Item
                name="importance"
                label="重要性调整"
                initialValue={arbitrationData.importance}
                rules={[{ required: true, message: '请选择重要性' }]}
              >
                <Select
                  options={[
                    { label: '低 (1)', value: 1 },
                    { label: '中 (3)', value: 3 },
                    { label: '高 (5)', value: 5 },
                    { label: '很高 (7)', value: 7 },
                    { label: '极高 (10)', value: 10 },
                  ]}
                />
              </Form.Item>
              <Form.Item>
                <Space>
                  <Button type="primary" htmlType="submit">执行仲裁</Button>
                  <Button onClick={() => setShowArbitrationModal(false)}>取消</Button>
                </Space>
              </Form.Item>
            </Form>
          </div>
        )}
      </Modal>
    </div>
  )
}