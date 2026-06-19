/** Optimization Tab — 检索优化效果

功能:
  - 显示 Rerank/Decay 效果
  - 手动触发检索优化
  - 效果对比展示
  - 参数调整（importance 调整）
*/

import { useState, useCallback } from 'react'
import {
  Typography, Button, Space, Empty, Spin, Table, Modal, App,
  Slider, Switch, Card, Progress,
} from 'antd'
import {
  BarChartOutlined,
} from '@ant-design/icons'
import type { MemoryEntry, OptimizationResult } from '../types/memory'
import {
  getOptimizedMemories, triggerOptimization,
} from '../services/memory-entity-api'

const { Text, Title } = Typography
const { Meta } = Card

export function OptimizationTab() {
  const { message } = App.useApp()
  const [memories, setMemories] = useState<MemoryEntry[]>([])
  const [optimizationResult, setOptimizationResult] = useState<OptimizationResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [showResultModal, setShowResultModal] = useState(false)
  const [optimizationParams, setOptimizationParams] = useState({
    rerank: true,
    decay: true,
    importanceBoost: 1,
  })

  // 表格列定义
  const columns = [
    {
      title: '摘要',
      dataIndex: 'summary',
      key: 'summary',
      ellipsis: true,
      render: (text: string) => <Text>{text}</Text>,
    },
    {
      title: '综合分数',
      dataIndex: 'score',
      key: 'score',
      width: 120,
      render: (score: number) => (
        <Progress
          percent={Math.round((score || 0) * 100)}
          size="small"
          strokeColor="#1890ff"
          format={() => `${(score || 0).toFixed(3)}`}
        />
      ),
    },
    {
      title: 'Rerank 分数',
      dataIndex: 'rerankScore',
      key: 'rerankScore',
      width: 120,
      render: (score: number | null) => score != null ? (
        <Progress
          percent={Math.round(score * 100)}
          size="small"
          strokeColor="#52c41a"
          format={() => `${score.toFixed(3)}`}
        />
      ) : <Text type="secondary">-</Text>,
    },
    {
      title: '衰减因子',
      dataIndex: 'decayFactor',
      key: 'decayFactor',
      width: 100,
      render: (factor: number) => (
        <Text type={factor < 0.5 ? 'danger' : factor < 0.8 ? 'warning' : 'success'}>
          {(factor || 1).toFixed(3)}
        </Text>
      ),
    },
    {
      title: '重要度',
      dataIndex: 'importance',
      key: 'importance',
      width: 80,
    },
    {
      title: '激活度',
      dataIndex: 'activation',
      key: 'activation',
      width: 80,
      render: (act: number) => (act || 1).toFixed(2),
    },
  ]

  // 执行优化
  const handleOptimize = useCallback(async () => {
    setLoading(true)
    try {
      // 先执行优化
      const result = await triggerOptimization({
        importance_boost: optimizationParams.importanceBoost,
      })
      setOptimizationResult(result)

      // 再获取优化后的结果
      const data = await getOptimizedMemories({
        rerank: optimizationParams.rerank,
        decay: optimizationParams.decay,
      })
      setMemories(data)
      setShowResultModal(true)
    } catch (error) {
      message.error('优化失败')
    } finally {
      setLoading(false)
    }
  }, [optimizationParams])

  // 重置参数
  const handleReset = () => {
    setOptimizationParams({
      rerank: true,
      decay: true,
      importanceBoost: 1,
    })
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: 12 }}>
      {/* 参数控制区 */}
      <Card title="优化参数" style={{ flexShrink: 0 }}>
        <Space orientation="vertical" size={16} style={{ width: '100%' }}>
          <div>
            <Text strong>启用 Rerank:</Text>
            <Switch
              checked={optimizationParams.rerank}
              onChange={(checked) => setOptimizationParams(prev => ({ ...prev, rerank: checked }))}
            />
          </div>
          <div>
            <Text strong>启用 Decay:</Text>
            <Switch
              checked={optimizationParams.decay}
              onChange={(checked) => setOptimizationParams(prev => ({ ...prev, decay: checked }))}
            />
          </div>
          <div>
            <Text strong>重要性提升:</Text>
            <Slider
              min={0}
              max={10}
              step={1}
              value={optimizationParams.importanceBoost}
              onChange={(value) => setOptimizationParams(prev => ({ ...prev, importanceBoost: value }))}
              style={{ width: 200 }}
            />
            <Text type="secondary" style={{ marginLeft: 8 }}>
              当前值: {optimizationParams.importanceBoost}
            </Text>
          </div>
          <Space>
            <Button
              type="primary"
              icon={<BarChartOutlined />}
              onClick={handleOptimize}
              loading={loading}
            >
              执行优化
            </Button>
            <Button onClick={handleReset}>重置参数</Button>
          </Space>
        </Space>
      </Card>

      {/* 结果展示区 */}
      <div style={{ flex: 1, overflow: 'auto', minHeight: 0 }}>
        {loading ? (
          <div style={{ display: 'flex', justifyContent: 'center', paddingTop: 60 }}>
            <Spin />
          </div>
        ) : memories.length === 0 ? (
          <Empty
            description="暂无优化结果，点击「执行优化」开始"
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          />
        ) : (
          <Table
            columns={columns}
            dataSource={memories}
            rowKey="id"
            pagination={{ pageSize: 20 }}
          />
        )}
      </div>

      {/* 优化结果弹窗 */}
      <Modal
        title="优化结果"
        open={showResultModal}
        onCancel={() => setShowResultModal(false)}
        footer={null}
        width={500}
      >
        {optimizationResult && (
          <div>
            <div style={{ marginBottom: 16 }}>
              <Title level={4}>优化统计</Title>
            </div>
            <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
              <Card style={{ flex: 1, minWidth: 150 }}>
                <Meta
                  title="优化记忆数量"
                  description={optimizationResult.optimizedCount}
                />
              </Card>
              <Card style={{ flex: 1, minWidth: 150 }}>
                <Meta
                  title="Rerank 改进"
                  description={optimizationResult.rerankImproved}
                />
              </Card>
              <Card style={{ flex: 1, minWidth: 150 }}>
                <Meta
                  title="Decay 应用"
                  description={optimizationResult.decayApplied}
                />
              </Card>
              <Card style={{ flex: 1, minWidth: 150 }}>
                <Meta
                  title="新增洞察"
                  description={optimizationResult.newInsights}
                />
              </Card>
            </div>
            <div style={{ marginTop: 16 }}>
              <Text>
                优化完成！Rerank 提升了 {optimizationResult.rerankImproved} 个记忆的排序，
                Decay 应用于 {optimizationResult.decayApplied} 个记忆，
                并发现了 {optimizationResult.newInsights} 个新洞察。
              </Text>
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}