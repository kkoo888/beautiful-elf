/** 节点详情抽屉 — 显示实体详情 */

import { useState, useCallback, useEffect } from 'react'
import { Drawer, Typography, Tag, Space, Button, Input, App, Popconfirm } from 'antd'
import {
  EditOutlined, SaveOutlined, DeleteOutlined,
  UserOutlined, ToolOutlined, ProjectOutlined, BulbOutlined,
  BankOutlined, NodeIndexOutlined,
} from '@ant-design/icons'
import { useGraphStore } from './graph-store'
import { updateEntity, deleteEntity } from '../services/memory-entity-api'

const { Text } = Typography
const { TextArea } = Input

const ENTITY_TYPE_MAP: Record<string, { icon: React.ReactNode; label: string; color: string }> = {
  person:  { icon: <UserOutlined />,    label: '人物', color: 'blue' },
  tech:    { icon: <ToolOutlined />,    label: '技术', color: 'cyan' },
  project: { icon: <ProjectOutlined />, label: '项目', color: 'purple' },
  tool:    { icon: <ToolOutlined />,    label: '工具', color: 'green' },
  concept: { icon: <BulbOutlined />,    label: '概念', color: 'orange' },
  org:     { icon: <BankOutlined />,    label: '组织', color: 'geekblue' },
}

const RELATION_LABEL: Record<string, string> = {
  uses: '使用', depends: '依赖', belongs: '属于',
  creates: '创建', works_at: '就职于', related: '相关',
  causes: '导致', enables: '使能', prevents: '阻止',
}

export function NodeDetailDrawer() {
  const { message } = App.useApp()
  const { selectedNodeId, detailDrawerOpen, closeDetailDrawer, nodes, edges, setNodes, setEdges, pushSnapshot } = useGraphStore()
  const selectedNode = nodes.find(n => n.id === selectedNodeId)

  const [editing, setEditing] = useState(false)
  const [editName, setEditName] = useState('')
  const [editDescription, setEditDescription] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    setEditing(false)
  }, [selectedNodeId])

  const handleEditStart = useCallback(() => {
    if (!selectedNode) return
    setEditName(selectedNode.data.name || '')
    setEditDescription(selectedNode.data.description || '')
    setEditing(true)
  }, [selectedNode])

  const handleSave = useCallback(async () => {
    if (!selectedNode) return
    const entityId = selectedNode.data.entityId
    if (!entityId) {
      message.warning('本地节点暂未保存，请先通过实体 Tab 创建')
      return
    }
    setSaving(true)
    try {
      await updateEntity(entityId, { name: editName, description: editDescription })
      setNodes(nodes.map(n =>
        n.id === selectedNodeId
          ? { ...n, data: { ...n.data, name: editName, description: editDescription } }
          : n
      ))
      setEditing(false)
      message.success('保存成功')
    } catch {
      message.error('保存失败')
    } finally {
      setSaving(false)
    }
  }, [selectedNode, editName, editDescription, selectedNodeId, nodes, setNodes])

  const handleDelete = useCallback(async () => {
    if (!selectedNode) return
    const entityId = selectedNode.data.entityId
    try {
      if (entityId) await deleteEntity(entityId)
      pushSnapshot()
      setNodes(nodes.filter(n => n.id !== selectedNodeId))
      setEdges(edges.filter(e => e.source !== selectedNodeId && e.target !== selectedNodeId))
      closeDetailDrawer()
      message.success('已删除')
    } catch {
      message.error('删除失败')
    }
  }, [selectedNode, selectedNodeId, nodes, edges, setNodes, setEdges, closeDetailDrawer])

  if (!selectedNode) return null

  const data = selectedNode.data
  const typeInfo = ENTITY_TYPE_MAP[data.entityType] || ENTITY_TYPE_MAP.concept

  // 找出与该实体相关的所有连线
  const connectedEdges = edges.filter(e => e.source === selectedNodeId || e.target === selectedNodeId)

  return (
    <Drawer
      title={
        <Space size={8}>
          {typeInfo.icon}
          <span>实体详情</span>
        </Space>
      }
      open={detailDrawerOpen}
      onClose={closeDetailDrawer}
      size="default"
      destroyOnHidden
      extra={
        editing ? (
          <Space size={8}>
            <Button size="small" onClick={() => setEditing(false)}>取消</Button>
            <Button size="small" type="primary" icon={<SaveOutlined />} loading={saving} onClick={handleSave}>保存</Button>
          </Space>
        ) : (
          <Space size={8}>
            <Button size="small" type="text" icon={<EditOutlined />} onClick={handleEditStart}>编辑</Button>
            <Popconfirm title="确认删除？" onConfirm={handleDelete} okText="删除" cancelText="取消">
              <Button size="small" type="text" danger icon={<DeleteOutlined />}>删除</Button>
            </Popconfirm>
          </Space>
        )
      }
    >
      {editing ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div>
            <Text style={{ fontSize: 12, color: '#8c8c8c', marginBottom: 4, display: 'block' }}>名称</Text>
            <Input value={editName} onChange={e => setEditName(e.target.value)} />
          </div>
          <div>
            <Text style={{ fontSize: 12, color: '#8c8c8c', marginBottom: 4, display: 'block' }}>描述</Text>
            <TextArea rows={4} value={editDescription} onChange={e => setEditDescription(e.target.value)} />
          </div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* 类型 + 名称 */}
          <div>
            <Tag color={typeInfo.color} icon={typeInfo.icon}>{typeInfo.label}</Tag>
            <Text strong style={{ fontSize: 16, marginLeft: 8 }}>{data.name}</Text>
          </div>

          {/* 描述 */}
          {data.description ? (
            <div style={{
              whiteSpace: 'pre-wrap', lineHeight: 1.8, fontSize: 14,
              padding: 12, background: '#fafafa', borderRadius: 6,
              border: '1px solid #f0f0f0',
            }}>
              {data.description}
            </div>
          ) : (
            <Text type="secondary" style={{ fontSize: 13 }}>暂无描述</Text>
          )}

          {/* 提及次数 */}
          <div>
            <Text style={{ fontSize: 12, color: '#8c8c8c' }}>
              被提及 <Text strong>{data.mentionCount ?? 0}</Text> 次
            </Text>
          </div>

          {/* 关联关系 */}
          {connectedEdges.length > 0 && (
            <div>
              <Text style={{ fontSize: 12, color: '#8c8c8c', marginBottom: 8, display: 'block' }}>
                <NodeIndexOutlined style={{ marginRight: 4 }} />
                关联关系 ({connectedEdges.length})
              </Text>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {connectedEdges.map(e => {
                  const isSource = e.source === selectedNodeId
                  const otherId = isSource ? e.target : e.source
                  const otherNode = nodes.find(n => n.id === otherId)
                  const relLabel = RELATION_LABEL[e.data?.relationType] || e.data?.relationType || '相关'
                  return (
                    <div key={e.id} style={{
                      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                      padding: '6px 10px', background: '#fafafa', borderRadius: 6, fontSize: 12,
                    }}>
                      <span>
                        {isSource ? '→' : '←'} {otherNode?.data?.name || otherId}
                        <Tag style={{ marginLeft: 6, fontSize: 10 }}>{relLabel}</Tag>
                        {e.data?.weight > 1 && <Text type="secondary" style={{ fontSize: 10 }}> x{e.data.weight}</Text>}
                      </span>
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </Drawer>
  )
}
