/** 工具新增/编辑弹窗 */

import { useEffect } from 'react'
import { Modal, Form, Input, Select, Space } from 'antd'
import type { ToolInfo, CreateToolInput, UpdateToolInput } from '../types/tools'

const { TextArea } = Input

interface ToolFormModalProps {
  open: boolean
  tool?: ToolInfo | null
  onOk: (values: CreateToolInput | UpdateToolInput) => void
  onCancel: () => void
  confirmLoading?: boolean
}

const RISK_OPTIONS = [
  { value: 'low', label: '🟢 低风险' },
  { value: 'medium', label: '🟡 中风险' },
  { value: 'high', label: '🔴 高风险' },
]

const MODULE_OPTIONS = [
  { value: '增', label: '增' },
  { value: '删', label: '删' },
  { value: '改', label: '改' },
  { value: '查', label: '查' },
  { value: '计算', label: '计算' },
  { value: '其他', label: '其他' },
]

/** 默认 JSON Schema 模板 */
const DEFAULT_SCHEMA = JSON.stringify(
  { type: 'object', properties: {}, required: [] },
  null, 2,
)

export function ToolFormModal({ open, tool, onOk, onCancel, confirmLoading }: ToolFormModalProps) {
  const [form] = Form.useForm()
  const isEdit = !!tool

  useEffect(() => {
    if (open) {
      if (tool) {
        form.setFieldsValue({
          name: tool.name,
          displayName: tool.displayName,
          description: tool.description,
          module: tool.module,
          riskLevel: tool.riskLevel ?? 'low',
          jsonSchema: JSON.stringify(tool.jsonSchema, null, 2),
        })
      } else {
        form.resetFields()
        form.setFieldsValue({
          riskLevel: 'low',
          module: 'builtin',
          jsonSchema: DEFAULT_SCHEMA,
        })
      }
    }
  }, [open, tool, form])

  const handleOk = async () => {
    try {
      const values = await form.validateFields()
      const parsed = {
        ...values,
        jsonSchema: JSON.parse(values.jsonSchema),
      }
      onOk(parsed)
    } catch {
      // validation failed, do nothing
    }
  }

  return (
    <Modal
      title={isEdit ? '✏️ 编辑工具' : '➕ 新增工具'}
      open={open}
      onOk={handleOk}
      onCancel={onCancel}
      confirmLoading={confirmLoading}
      width={640}
      destroyOnClose
    >
      <Form form={form} layout="vertical" autoComplete="off">
        <Form.Item
          name="name"
          label="工具名称"
          rules={[
            { required: true, message: '请输入工具名称' },
            { pattern: /^[a-z_][a-z0-9_]*$/, message: '仅允许小写字母、数字和下划线' },
          ]}
        >
          <Input placeholder="例如: web_search" disabled={isEdit} />
        </Form.Item>

        <Form.Item name="displayName" label="显示名称">
          <Input placeholder="例如: 联网搜索" />
        </Form.Item>

        <Form.Item
          name="description"
          label="描述"
          rules={[{ required: true, message: '请输入工具描述' }]}
        >
          <TextArea rows={2} placeholder="描述工具的功能和用途" />
        </Form.Item>

        <Space size="middle" style={{ display: 'flex' }}>
          <Form.Item
            name="module"
            label="所属模块"
            rules={[{ required: true }]}
            style={{ flex: 1 }}
          >
            <Select options={MODULE_OPTIONS} placeholder="选择模块" />
          </Form.Item>

          <Form.Item
            name="riskLevel"
            label="风险等级"
            rules={[{ required: true }]}
            style={{ flex: 1 }}
          >
            <Select options={RISK_OPTIONS} />
          </Form.Item>
        </Space>

        <Form.Item
          name="jsonSchema"
          label="参数 Schema (JSON)"
          rules={[
            { required: true, message: '请输入 JSON Schema' },
            {
              validator: (_, value) => {
                try {
                  JSON.parse(value)
                  return Promise.resolve()
                } catch {
                  return Promise.reject(new Error('JSON 格式不合法'))
                }
              },
            },
          ]}
        >
          <TextArea
            rows={8}
            placeholder={DEFAULT_SCHEMA}
            style={{ fontFamily: 'monospace', fontSize: 12 }}
          />
        </Form.Item>
      </Form>
    </Modal>
  )
}
