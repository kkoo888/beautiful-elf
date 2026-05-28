/** 节点配置抽屉（右侧面板） */

import { Drawer, Form, Input, Select, Tag, Button, Space, Typography } from 'antd'
import { DeleteOutlined } from '@ant-design/icons'
import { useEffect } from 'react'
import type { WorkflowNode, DagNodeType } from '../types/workflow'
import { NODE_TYPE_LABEL } from './workflow-editor'

const { Text } = Typography

interface NodeConfigDrawerProps {
  node: WorkflowNode | null
  open: boolean
  onClose: () => void
  onUpdate: (node: WorkflowNode) => void
  onDelete: (nodeId: string) => void
}

export function NodeConfigDrawer({ node, open, onClose, onUpdate, onDelete }: NodeConfigDrawerProps) {
  const [form] = Form.useForm()

  useEffect(() => {
    if (node) {
      form.setFieldsValue({
        label: node.label,
        type: node.type,
        ...node.config,
      })
    }
  }, [node, form])

  const handleSave = () => {
    if (!node) return
    const values = form.getFieldsValue()
    const { label, type, ...rest } = values
    onUpdate({
      ...node,
      label,
      type: type as DagNodeType,
      config: rest,
    })
    onClose()
  }

  if (!node) return null

  const typeInfo = NODE_TYPE_LABEL[node.type]

  return (
    <Drawer
      title={
        <Space>
          <span>节点配置</span>
          <Tag color={typeInfo.color}>{typeInfo.label}</Tag>
        </Space>
      }
      placement="right"
      width={320}
      open={open}
      onClose={onClose}
      extra={
        <Button
          danger
          type="text"
          size="small"
          icon={<DeleteOutlined />}
          onClick={() => {
            onDelete(node.id)
            onClose()
          }}
        >
          删除
        </Button>
      }
      footer={
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
          <Button onClick={onClose}>取消</Button>
          <Button type="primary" onClick={handleSave}>
            保存
          </Button>
        </div>
      }
    >
      <Form form={form} layout="vertical" size="small">
        <Form.Item label="节点名称" name="label" rules={[{ required: true, message: '请输入节点名称' }]}>
          <Input placeholder="输入节点名称" />
        </Form.Item>
        <Form.Item label="节点类型" name="type">
          <Select
            options={Object.entries(NODE_TYPE_LABEL).map(([key, val]) => ({
              value: key,
              label: (
                <Space>
                  <Tag color={val.color}>{val.label}</Tag>
                </Space>
              ),
            }))}
          />
        </Form.Item>
        <Form.Item label="描述" name="description">
          <Input.TextArea rows={2} placeholder="节点描述（可选）" />
        </Form.Item>
        <Form.Item label="超时时间(秒)" name="timeout">
          <Input type="number" placeholder="默认不限" />
        </Form.Item>
        <Form.Item label="重试次数" name="retryCount">
          <Input type="number" placeholder="默认 0" />
        </Form.Item>
      </Form>
      <div style={{ marginTop: 16 }}>
        <Text type="secondary" style={{ fontSize: 12 }}>
          ID: {node.id}
        </Text>
      </div>
    </Drawer>
  )
}
