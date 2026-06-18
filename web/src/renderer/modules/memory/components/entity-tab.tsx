/** 实体记忆 Tab — 借鉴 Hindsight TEMPR 实体管理

功能:
  - 实体列表（按类型/关键词筛选）
  - 实体详情（点击打开 Drawer）
  - 新建/编辑/删除实体
  - 关系管理
*/

import { useState, useEffect, useCallback } from 'react'
import {
  Typography, Button, Space, Empty, Spin, Tag, App,
  Drawer, Form, Input, Select, Popconfirm, Tooltip, Segmented,
} from 'antd'
import {
  PlusOutlined, ReloadOutlined, EditOutlined, DeleteOutlined,
  UserOutlined, ToolOutlined, ProjectOutlined, BulbOutlined,
  ApartmentOutlined, BankOutlined, NodeIndexOutlined,
} from '@ant-design/icons'
import {
  listEntities, createEntity, updateEntity, deleteEntity,
  listRelations, createRelation, deleteRelation,
  type MemoryEntity, type EntityRelation,
} from '../services/memory-entity-api'

const { Text } = Typography
const { TextArea } = Input

const ENTITY_TYPE_MAP: Record<string, { icon: React.ReactNode; label: string; color: string }> = {
  person: { icon: <UserOutlined />, label: '人物', color: 'blue' },
  tech: { icon: <ToolOutlined />, label: '技术', color: 'cyan' },
  project: { icon: <ProjectOutlined />, label: '项目', color: 'purple' },
  tool: { icon: <ToolOutlined />, label: '工具', color: 'green' },
  concept: { icon: <BulbOutlined />, label: '概念', color: 'orange' },
  org: { icon: <BankOutlined />, label: '组织', color: 'geekblue' },
}

const RELATION_TYPE_MAP: Record<string, string> = {
  uses: '使用',
  depends: '依赖',
  belongs: '属于',
  creates: '创建',
  works_at: '就职于',
  related: '相关',
}

export function EntityTab() {
  const { message } = App.useApp()
  const [entities, setEntities] = useState<MemoryEntity[]>([])
  const [loading, setLoading] = useState(true)
  const [typeFilter, setTypeFilter] = useState<string>('all')
  const [keyword, setKeyword] = useState('')
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [editingEntity, setEditingEntity] = useState<MemoryEntity | null>(null)
  const [relations, setRelations] = useState<EntityRelation[]>([])
  const [form] = Form.useForm()

  const loadEntities = useCallback(async () => {
    setLoading(true)
    try {
      const params: any = { pageSize: 200 }
      if (typeFilter !== 'all') params.entityType = typeFilter
      if (keyword) params.keyword = keyword
      const { items } = await listEntities(params)
      setEntities(items)
    } catch {} finally {
      setLoading(false)
    }
  }, [typeFilter, keyword])

  useEffect(() => { loadEntities() }, [loadEntities])

  const loadRelations = useCallback(async (entityId: number) => {
    try {
      const rels = await listRelations(entityId)
      setRelations(rels)
    } catch { setRelations([]) }
  }, [])

  const handleCreate = () => {
    setEditingEntity(null)
    form.resetFields()
    form.setFieldsValue({ entityType: 'concept' })
    setDrawerOpen(true)
  }

  const handleEdit = (entity: MemoryEntity) => {
    setEditingEntity(entity)
    form.setFieldsValue({
      name: entity.name,
      entityType: entity.entityType,
      description: entity.description,
      aliases: entity.aliases,
    })
    loadRelations(entity.id)
    setDrawerOpen(true)
  }

  const handleSave = async () => {
    try {
      const values = await form.validateFields()
      if (editingEntity) {
        await updateEntity(editingEntity.id, values)
        message.success('更新成功')
      } else {
        await createEntity(values)
        message.success('创建成功')
      }
      setDrawerOpen(false)
      loadEntities()
    } catch { message.error('保存失败') }
  }

  const handleDelete = async (id: number) => {
    try {
      await deleteEntity(id)
      message.success('已删除')
      loadEntities()
    } catch { message.error('删除失败') }
  }

  const typeOptions = [
    { label: '全部', value: 'all' },
    ...Object.entries(ENTITY_TYPE_MAP).map(([k, v]) => ({ label: `${v.label}`, value: k })),
  ]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: 12 }}>
      {/* 工具栏 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexShrink: 0 }}>
        <Segmented
          value={typeFilter}
          onChange={v => setTypeFilter(v as string)}
          options={typeOptions}
          size="small"
        />
        <Space size={8}>
          <Tooltip title="刷新"><Button type="text" size="small" icon={<ReloadOutlined />} onClick={loadEntities} /></Tooltip>
          <Button type="primary" size="small" icon={<PlusOutlined />} onClick={handleCreate}>新建实体</Button>
        </Space>
      </div>

      {/* 列表 */}
      <div style={{ flex: 1, overflow: 'auto', minHeight: 0 }}>
        {loading ? (
          <div style={{ display: 'flex', justifyContent: 'center', paddingTop: 60 }}><Spin /></div>
        ) : entities.length === 0 ? (
          <Empty description="暂无实体，点击「新建实体」开始" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        ) : (
          <div>
            {entities.map((entity, index) => {
              const typeInfo = ENTITY_TYPE_MAP[entity.entityType] || ENTITY_TYPE_MAP.concept
              return (
                <div
                  key={entity.id}
                  style={{
                    padding: '12px 0',
                    borderBottom: index < entities.length - 1 ? '1px solid #f0f0f0' : 'none',
                    cursor: 'pointer',
                  }}
                  onClick={() => handleEdit(entity)}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Space size={8}>
                      <Tag color={typeInfo.color} icon={typeInfo.icon} style={{ margin: 0 }}>
                        {typeInfo.label}
                      </Tag>
                      <Text strong style={{ fontSize: 14 }}>{entity.name}</Text>
                      {entity.aliases && (
                        <Text type="secondary" style={{ fontSize: 11 }}>({entity.aliases})</Text>
                      )}
                    </Space>
                    <Space size={4}>
                      <Text type="secondary" style={{ fontSize: 11 }}>
                        提及 {entity.mentionCount} 次
                      </Text>
                      <Popconfirm title="确认删除？" onConfirm={(e) => { e?.stopPropagation(); handleDelete(entity.id) }} okText="删除" cancelText="取消">
                        <Button type="text" size="small" icon={<DeleteOutlined />} style={{ color: '#bfbfbf' }} onClick={e => e.stopPropagation()} />
                      </Popconfirm>
                    </Space>
                  </div>
                  {entity.description && (
                    <div style={{ marginTop: 4, fontSize: 12, color: '#8c8c8c', lineHeight: 1.6 }}>
                      {entity.description.length > 100 ? entity.description.slice(0, 100) + '...' : entity.description}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* 详情/编辑 Drawer */}
      <Drawer
        title={editingEntity ? '编辑实体' : '新建实体'}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        width={380}
        destroyOnHidden
        extra={
          <Button type="primary" onClick={handleSave}>
            {editingEntity ? '保存' : '创建'}
          </Button>
        }
      >
        <Form form={form} layout="vertical" size="small">
          <Form.Item name="name" label="名称" rules={[{ required: true, message: '请输入名称' }]}>
            <Input placeholder="如：React、张三、beautiful-elf" />
          </Form.Item>
          <Form.Item name="entityType" label="类型">
            <Select options={Object.entries(ENTITY_TYPE_MAP).map(([k, v]) => ({
              value: k, label: `${v.label}`,
            }))} />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <TextArea rows={3} placeholder="实体描述（可自动从记忆中提取）" />
          </Form.Item>
          <Form.Item name="aliases" label="别名" extra="多个别名用逗号分隔">
            <Input placeholder="如：react.js,ReactJS" />
          </Form.Item>
        </Form>

        {/* 关系列表 */}
        {editingEntity && relations.length > 0 && (
          <div style={{ marginTop: 16 }}>
            <Text strong style={{ fontSize: 13, marginBottom: 8, display: 'block' }}>
              <NodeIndexOutlined style={{ marginRight: 4 }} />
              关联关系 ({relations.length})
            </Text>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {relations.map(rel => {
                const isSource = rel.sourceEntityId === editingEntity.id
                const otherId = isSource ? rel.targetEntityId : rel.sourceEntityId
                const otherEntity = entities.find(e => e.id === otherId)
                return (
                  <div key={rel.id} style={{
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                    padding: '6px 10px', background: '#fafafa', borderRadius: 6, fontSize: 12,
                  }}>
                    <span>
                      {isSource ? '→' : '←'} {otherEntity?.name || `实体#${otherId}`}
                      <Tag style={{ marginLeft: 6, fontSize: 10 }}>{RELATION_TYPE_MAP[rel.relationType] || rel.relationType}</Tag>
                      {rel.weight > 1 && <Text type="secondary" style={{ fontSize: 10 }}> ×{rel.weight}</Text>}
                    </span>
                    <Popconfirm title="确认删除关系？" onConfirm={() => deleteRelation(rel.id).then(loadEntities)} okText="删除" cancelText="取消">
                      <Button type="text" size="small" icon={<DeleteOutlined />} style={{ color: '#bfbfbf', padding: 0 }} />
                    </Popconfirm>
                  </div>
                )
              })}
            </div>
          </div>
        )}
      </Drawer>
    </div>
  )
}
