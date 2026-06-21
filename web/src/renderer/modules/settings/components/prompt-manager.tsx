/**
 * Prompt 管理主面板
 * 提供 Prompt 列表、新建/编辑/删除、版本历史、A/B 测试配置
 */

import { useCallback, useMemo, useState } from 'react'
import {
  Button,
  Modal,
  Form,
  Input,
  Table,
  Tag,
  Space,
  Popconfirm,
  Switch,
  InputNumber,
  Typography,
  message,
} from 'antd'
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  HistoryOutlined,
  ExperimentOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import type { PromptConfig, ABTestConfig } from '../types/settings'
import { PromptVersionHistory } from './prompt-version-history'

const { TextArea } = Input
const { Text } = Typography

/** 生成唯一 ID */
const genId = (): string => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`

/** 初始 mock 数据 */
const INITIAL_PROMPTS: PromptConfig[] = [
  {
    id: 'p1',
    name: '默认对话 Prompt',
    description: '通用对话场景使用的系统提示词',
    versions: [
      {
        id: 'v1-1',
        version: 1,
        content: '你是一个友好的主人的知识最前沿的军师，请用中文回答用户问题。',
        createdAt: Date.now() - 86400000 * 3,
        createdBy: '系统',
        isActive: false,
      },
      {
        id: 'v1-2',
        version: 2,
        content:
          '你是一个友好的主人的知识最前沿的军师。请用简洁清晰的中文回答用户问题，必要时可使用 Markdown 格式化输出。',
        createdAt: Date.now() - 86400000,
        createdBy: '管理员',
        isActive: true,
      },
    ],
    activeVersionId: 'v1-2',
    abTest: { enabled: false, variants: [] },
  },
  {
    id: 'p2',
    name: '代码助手 Prompt',
    description: '编程辅助场景使用的系统提示词',
    versions: [
      {
        id: 'v2-1',
        version: 1,
        content:
          '你是一个专业的编程专家，擅长 TypeScript、React 和 Node.js。请提供高质量的代码建议。',
        createdAt: Date.now() - 86400000 * 7,
        createdBy: '系统',
        isActive: true,
      },
    ],
    activeVersionId: 'v2-1',
  },
]

/** Prompt 管理组件 */
export function PromptManager() {
  const [prompts, setPrompts] = useState<PromptConfig[]>(INITIAL_PROMPTS)
  const [editingPrompt, setEditingPrompt] = useState<PromptConfig | null>(null)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [historyPrompt, setHistoryPrompt] = useState<PromptConfig | null>(null)
  const [abTestPrompt, setAbTestPrompt] = useState<PromptConfig | null>(null)
  const [form] = Form.useForm()
  const [abForm] = Form.useForm()

  // ── 新建 / 编辑 ──────────────────────────────────────
  const openCreate = useCallback(() => {
    setEditingPrompt(null)
    form.resetFields()
    setIsModalOpen(true)
  }, [form])

  const openEdit = useCallback(
    (record: PromptConfig) => {
      setEditingPrompt(record)
      form.setFieldsValue({ name: record.name, description: record.description })
      setIsModalOpen(true)
    },
    [form]
  )

  const handleModalOk = useCallback(() => {
    form.validateFields().then((values) => {
      if (editingPrompt) {
        // 编辑
        setPrompts((prev) =>
          prev.map((p) =>
            p.id === editingPrompt.id
              ? { ...p, name: values.name, description: values.description }
              : p
          )
        )
        message.success('Prompt 已更新')
      } else {
        // 新建
        const newPrompt: PromptConfig = {
          id: genId(),
          name: values.name,
          description: values.description,
          versions: [
            {
              id: genId(),
              version: 1,
              content: '',
              createdAt: Date.now(),
              createdBy: '当前用户',
              isActive: true,
            },
          ],
          activeVersionId: '',
        }
        newPrompt.activeVersionId = newPrompt.versions[0].id
        setPrompts((prev) => [...prev, newPrompt])
        message.success('Prompt 已创建')
      }
      setIsModalOpen(false)
    })
  }, [editingPrompt, form])

  // ── 删除 ─────────────────────────────────────────────
  const handleDelete = useCallback((id: string) => {
    setPrompts((prev) => prev.filter((p) => p.id !== id))
    message.success('已删除')
  }, [])

  // ── 版本历史回调 ─────────────────────────────────────
  const handleSetActive = useCallback((promptId: string, versionId: string) => {
    setPrompts((prev) =>
      prev.map((p) => {
        if (p.id !== promptId) return p
        const versions = p.versions.map((v) => ({
          ...v,
          isActive: v.id === versionId,
        }))
        return { ...p, versions, activeVersionId: versionId }
      })
    )
  }, [])

  // ── A/B 测试 ─────────────────────────────────────────
  const openAbTest = useCallback(
    (record: PromptConfig) => {
      setAbTestPrompt(record)
      const variants =
        record.abTest?.variants.map((v) => ({ ...v })) ??
        record.versions.map((v) => ({ versionId: v.id, weight: 100 / record.versions.length }))
      abForm.setFieldsValue({
        enabled: record.abTest?.enabled ?? false,
        variants,
      })
    },
    [abForm]
  )

  const handleAbTestOk = useCallback(() => {
    abForm.validateFields().then((values) => {
      if (!abTestPrompt) return
      const abTest: ABTestConfig = {
        enabled: values.enabled,
        variants: values.variants.map((v: { versionId: string; weight: number }) => ({
          versionId: v.versionId,
          weight: v.weight,
        })),
      }
      setPrompts((prev) => prev.map((p) => (p.id === abTestPrompt.id ? { ...p, abTest } : p)))
      setAbTestPrompt(null)
      message.success('A/B 测试配置已保存')
    })
  }, [abForm, abTestPrompt])

  // ── 表格列定义 ───────────────────────────────────────
  const columns = useMemo<ColumnsType<PromptConfig>>(
    () => [
      {
        title: '名称',
        dataIndex: 'name',
        key: 'name',
        render: (name: string, record) => (
          <div>
            <Text strong>{name}</Text>
            <br />
            <Text type="secondary" style={{ fontSize: 12 }}>
              {record.description}
            </Text>
          </div>
        ),
      },
      {
        title: '版本数',
        key: 'versionCount',
        width: 80,
        align: 'center',
        render: (_, record) => <Tag>{record.versions.length}</Tag>,
      },
      {
        title: '激活版本',
        key: 'activeVersion',
        width: 100,
        render: (_, record) => {
          const active = record.versions.find((v) => v.id === record.activeVersionId)
          return active ? <Tag color="green">v{active.version}</Tag> : <Tag>—</Tag>
        },
      },
      {
        title: 'A/B 测试',
        key: 'abTest',
        width: 100,
        align: 'center',
        render: (_, record) =>
          record.abTest?.enabled ? <Tag color="blue">已开启</Tag> : <Tag>关闭</Tag>,
      },
      {
        title: '操作',
        key: 'actions',
        width: 260,
        render: (_, record) => (
          <Space size="small">
            <Button
              type="link"
              size="small"
              icon={<EditOutlined />}
              onClick={() => openEdit(record)}
            >
              编辑
            </Button>
            <Button
              type="link"
              size="small"
              icon={<HistoryOutlined />}
              onClick={() => setHistoryPrompt(record)}
            >
              历史
            </Button>
            <Button
              type="link"
              size="small"
              icon={<ExperimentOutlined />}
              onClick={() => openAbTest(record)}
            >
              A/B
            </Button>
            <Popconfirm
              title="确定删除该 Prompt？"
              description="删除后不可恢复"
              onConfirm={() => handleDelete(record.id)}
              okText="删除"
              cancelText="取消"
              okButtonProps={{ danger: true }}
            >
              <Button type="link" size="small" danger icon={<DeleteOutlined />}>
                删除
              </Button>
            </Popconfirm>
          </Space>
        ),
      },
    ],
    [openEdit, openAbTest, handleDelete]
  )

  // ── 渲染 ─────────────────────────────────────────────
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Text strong style={{ fontSize: 15 }}>
          Prompt 管理
        </Text>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
          新建 Prompt
        </Button>
      </div>

      <Table<PromptConfig>
        rowKey="id"
        columns={columns}
        dataSource={prompts}
        pagination={false}
        size="middle"
      />

      {/* 新建/编辑 Modal */}
      <Modal
        title={editingPrompt ? '编辑 Prompt' : '新建 Prompt'}
        open={isModalOpen}
        onOk={handleModalOk}
        onCancel={() => setIsModalOpen(false)}
        okText="保存"
        cancelText="取消"
        destroyOnHidden
      >
        <Form form={form} layout="vertical" preserve={false}>
          <Form.Item
            name="name"
            label="名称"
            rules={[{ required: true, message: '请输入 Prompt 名称' }]}
          >
            <Input placeholder="例如：默认对话 Prompt" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <TextArea rows={2} placeholder="简要描述该 Prompt 的用途" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 版本历史 Modal */}
      {historyPrompt && (
        <PromptVersionHistory
          prompt={historyPrompt}
          open={!!historyPrompt}
          onClose={() => setHistoryPrompt(null)}
          onSetActive={(versionId) => handleSetActive(historyPrompt.id, versionId)}
        />
      )}

      {/* A/B 测试配置 Modal */}
      <Modal
        title={`A/B 测试 — ${abTestPrompt?.name ?? ''}`}
        open={!!abTestPrompt}
        onOk={handleAbTestOk}
        onCancel={() => setAbTestPrompt(null)}
        okText="保存"
        cancelText="取消"
        destroyOnHidden
        width={520}
      >
        {abTestPrompt && (
          <Form form={abForm} layout="vertical" preserve={false}>
            <Form.Item name="enabled" label="启用 A/B 测试" valuePropName="checked">
              <Switch />
            </Form.Item>
            <Form.List name="variants">
              {(fields) => (
                <>
                  {fields.map((field, index) => (
                    <Space
                      key={field.key}
                      align="baseline"
                      style={{ display: 'flex', marginBottom: 8 }}
                    >
                      <Form.Item {...field} name={[field.name, 'versionId']} noStyle>
                        <Input disabled style={{ width: 180 }} />
                      </Form.Item>
                      <Form.Item
                        {...field}
                        name={[field.name, 'weight']}
                        noStyle
                        rules={[{ required: true, message: '请输入权重' }]}
                      >
                        <InputNumber min={0} max={100} addonAfter="%" placeholder="权重" />
                      </Form.Item>
                    </Space>
                  ))}
                </>
              )}
            </Form.List>
            <Text type="secondary" style={{ fontSize: 12 }}>
              权重总和建议为 100%，系统按权重比例分配流量。
            </Text>
          </Form>
        )}
      </Modal>
    </div>
  )
}
