/** 节点详情抽屉 — 对标 Dify Panel，点击节点右侧展示详情 + 编辑 */

import { useState, useCallback, useEffect } from 'react'
import { Drawer, Typography, Tag, Space, Button, Input, App, Popconfirm, Select } from 'antd'
import {
  EditOutlined, SaveOutlined, DeleteOutlined,
  FileTextOutlined, BulbOutlined, LinkOutlined,
} from '@ant-design/icons'
import { useGraphStore } from './graph-store'
import { updateObservation, deleteObservation } from '../services/memory-api'

const { Text } = Typography
const { TextArea } = Input

const CATEGORY_MAP: Record<string, { icon: string; label: string; color: string }> = {
  decisions: { icon: '🔑', label: '决策', color: 'blue' },
  pitfalls: { icon: '🐛', label: '踩坑', color: 'red' },
  preferences: { icon: '👤', label: '偏好', color: 'purple' },
  status: { icon: '📦', label: '状态', color: 'green' },
}

export function NodeDetailDrawer() {
  const { message } = App.useApp()
  const { selectedNodeId, detailDrawerOpen, closeDetailDrawer, nodes, setNodes, observations } = useGraphStore()
  const selectedNode = nodes.find(n => n.id === selectedNodeId)

  const [editing, setEditing] = useState(false)
  const [editContent, setEditContent] = useState('')
  const [editCategory, setEditCategory] = useState('')
  const [saving, setSaving] = useState(false)

  // 重置编辑状态
  useEffect(() => {
    setEditing(false)
  }, [selectedNodeId])

  const handleEditStart = useCallback(() => {
    if (!selectedNode) return
    setEditContent(selectedNode.data.content || '')
    setEditCategory(selectedNode.data.category || 'decisions')
    setEditing(true)
  }, [selectedNode])

  const handleSave = useCallback(async () => {
    if (!selectedNode || selectedNode.type !== 'observation') return
    setSaving(true)
    try {
      const obsId = selectedNode.data.obsId
      await updateObservation(obsId, { content: editContent, category: editCategory })
      // 更新 store 中的节点数据
      setNodes(nodes.map(n =>
        n.id === selectedNodeId
          ? { ...n, data: { ...n.data, content: editContent, category: editCategory } }
          : n
      ))
      setEditing(false)
      message.success('保存成功')
    } catch {
      message.error('保存失败')
    } finally {
      setSaving(false)
    }
  }, [selectedNode, editContent, editCategory, selectedNodeId, nodes, setNodes])

  const handleDelete = useCallback(async () => {
    if (!selectedNode) return
    try {
      if (selectedNode.type === 'observation' && selectedNode.data.obsId) {
        await deleteObservation(selectedNode.data.obsId)
      }
      const { edges, setEdges, pushSnapshot } = useGraphStore.getState()
      pushSnapshot()
      setNodes(nodes.filter(n => n.id !== selectedNodeId))
      setEdges(edges.filter(e => e.source !== selectedNodeId && e.target !== selectedNodeId))
      closeDetailDrawer()
      message.success('已删除')
    } catch {
      message.error('删除失败')
    }
  }, [selectedNode, selectedNodeId, nodes, setNodes, closeDetailDrawer])

  if (!selectedNode) return null

  const isObservation = selectedNode.type === 'observation'
  const data = selectedNode.data
  const cat = CATEGORY_MAP[data.category]

  return (
    <Drawer
      title={
        <Space size={8}>
          {isObservation ? <BulbOutlined style={{ color: '#E8913A' }} /> : <FileTextOutlined style={{ color: '#3BA0E8' }} />}
          <span>{isObservation ? '提炼记忆详情' : '日志详情'}</span>
        </Space>
      }
      open={detailDrawerOpen}
      onClose={closeDetailDrawer}
      size="default"
      destroyOnHidden
      extra={
        isObservation ? (
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
        ) : null
      }
    >
      {isObservation && editing ? (
        /* ── 编辑模式 ── */
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div>
            <Text style={{ fontSize: 12, color: '#8c8c8c', marginBottom: 4, display: 'block' }}>分类</Text>
            <Select
              value={editCategory}
              onChange={setEditCategory}
              style={{ width: '100%' }}
              options={Object.entries(CATEGORY_MAP).map(([k, v]) => ({
                value: k, label: `${v.icon} ${v.label}`,
              }))}
            />
          </div>
          <div>
            <Text style={{ fontSize: 12, color: '#8c8c8c', marginBottom: 4, display: 'block' }}>内容</Text>
            <TextArea
              rows={8}
              value={editContent}
              onChange={e => setEditContent(e.target.value)}
              style={{ fontSize: 13, lineHeight: 1.8 }}
            />
          </div>
        </div>
      ) : (
        /* ── 查看模式 ── */
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* 分类 + 新鲜度 */}
          {isObservation && (
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              {cat && <Tag color={cat.color}>{cat.icon} {cat.label}</Tag>}
              {data.freshness && (
                <Text style={{ fontSize: 12, color: '#8c8c8c' }}>
                  新鲜度: {data.freshness}
                </Text>
              )}
            </div>
          )}

          {/* 内容 */}
          <div style={{
            whiteSpace: 'pre-wrap', lineHeight: 1.8, fontSize: 14,
            padding: 12, background: '#fafafa', borderRadius: 6,
            border: '1px solid #f0f0f0',
          }}>
            {data.content || data.title || '无内容'}
          </div>

          {/* 来源信息 */}
          {isObservation && data.sources && data.sources.length > 0 && (
            <div>
              <Text style={{ fontSize: 12, color: '#8c8c8c', marginBottom: 8, display: 'block' }}>
                <LinkOutlined style={{ marginRight: 4 }} />
                来源日志 ({data.sources.length})
              </Text>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {data.sources.map((src: any) => (
                  <div key={src.sourceId} style={{
                    padding: '6px 10px', background: '#f6f8fa', borderRadius: 6,
                    fontSize: 12, color: '#595959',
                  }}>
                    <FileTextOutlined style={{ marginRight: 4, color: '#3BA0E8' }} />
                    {src.logTitle}
                    {src.evidenceQuote && (
                      <div style={{ fontStyle: 'italic', color: '#8c8c8c', marginTop: 2, paddingLeft: 12 }}>
                        "{src.evidenceQuote}"
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </Drawer>
  )
}
