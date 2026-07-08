/**
 * 意图纠正按钮 + 弹窗
 * 用户点击后选择正确的模块，提交纠正记录
 */

import React, { useCallback, useState } from 'react'
import { Button, Tooltip, Modal, Select, Typography, Space, message } from 'antd'
import { AimOutlined, CheckCircleOutlined } from '@ant-design/icons'
import { createCorrection } from '@/modules/intent-learning/services/intent-api'

interface IntentCorrectionButtonProps {
  /** 原始意图文本（用户的消息内容） */
  originalIntent: string
  /** 意图路由结果（如果有） */
  intentRoute?: string
}

const MODULE_OPTIONS = [
  { value: '对话', label: '💬 对话' },
  { value: '日程', label: '📅 日程' },
  { value: '剪贴板', label: '📋 剪贴板' },
  { value: '代码片段', label: '💻 代码片段' },
  { value: '知识库', label: '📚 知识库' },
  { value: '记忆', label: '🧠 记忆' },
  { value: '翻译', label: '🌐 翻译' },
  { value: '技能', label: '⚡ 技能' },
  { value: '工作流', label: '🔄 工作流' },
  { value: '图片画廊', label: '🖼️ 图片画廊' },
  { value: '专家团', label: '👥 专家团' },
]

export const IntentCorrectionButton: React.FC<IntentCorrectionButtonProps> = ({
  originalIntent,
  intentRoute,
}) => {
  const [modalVisible, setModalVisible] = useState(false)
  const [selectedModule, setSelectedModule] = useState<string>()
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)

  const handleOpen = useCallback(() => {
    setModalVisible(true)
    setSelectedModule(undefined)
  }, [])

  const handleCancel = useCallback(() => {
    setModalVisible(false)
    setSelectedModule(undefined)
  }, [])

  const handleSubmit = useCallback(async () => {
    if (!selectedModule || submitting) return
    setSubmitting(true)
    try {
      await createCorrection(originalIntent, selectedModule)
      setSubmitted(true)
      setModalVisible(false)
      message.success('纠正成功，感谢反馈！')
      setTimeout(() => setSubmitted(false), 3000)
    } catch {
      message.error('提交失败，请稍后重试')
    } finally {
      setSubmitting(false)
    }
  }, [originalIntent, selectedModule, submitting])

  return (
    <>
      <Tooltip title={submitted ? '已纠正' : '纠正意图'}>
        <Button
          type="text"
          size="small"
          icon={submitted ? <CheckCircleOutlined /> : <AimOutlined />}
          onClick={handleOpen}
          style={{
            fontSize: 12,
            color: submitted ? '#52c41a' : 'rgba(0,0,0,0.35)',
            padding: '0 4px',
            height: 24,
          }}
        />
      </Tooltip>

      <Modal
        title={
          <Space>
            <AimOutlined style={{ color: '#1890ff' }} />
            <span>纠正意图</span>
          </Space>
        }
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={handleCancel}
        okText="提交纠正"
        cancelText="取消"
        okButtonProps={{ disabled: !selectedModule, loading: submitting }}
        width={420}
      >
        <div style={{ padding: '8px 0' }}>
          {originalIntent && (
            <div style={{ marginBottom: 16 }}>
              <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                用户消息
              </Typography.Text>
              <div style={{
                marginTop: 4,
                padding: '8px 12px',
                background: '#f5f5f5',
                borderRadius: 8,
                fontSize: 13,
                color: '#333',
                maxHeight: 80,
                overflow: 'auto',
              }}>
                {originalIntent.length > 100 ? originalIntent.slice(0, 100) + '...' : originalIntent}
              </div>
            </div>
          )}

          {intentRoute && (
            <div style={{ marginBottom: 16 }}>
              <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                当前识别为
              </Typography.Text>
              <div style={{ marginTop: 4 }}>
                <span style={{
                  display: 'inline-block',
                  padding: '2px 10px',
                  background: '#e6f7ff',
                  border: '1px solid #91d5ff',
                  borderRadius: 4,
                  fontSize: 12,
                  color: '#1890ff',
                }}>
                  {intentRoute}
                </span>
              </div>
            </div>
          )}

          <div>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              选择正确的模块
            </Typography.Text>
            <Select
              style={{ width: '100%', marginTop: 8 }}
              placeholder="这个意图应该路由到哪个模块？"
              options={MODULE_OPTIONS}
              value={selectedModule}
              onChange={setSelectedModule}
              size="middle"
              showSearch
              optionFilterProp="label"
            />
          </div>
        </div>
      </Modal>
    </>
  )
}
