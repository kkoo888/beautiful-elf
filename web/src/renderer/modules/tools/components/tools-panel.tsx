/** 工具管理主面板 */

import { useState } from 'react'
import { Button, Space } from 'antd'
import { ReloadOutlined, PlusOutlined } from '@ant-design/icons'
import { PageHeader } from '@/components/page-header'
import { useTools, useCreateTool, useUpdateTool, useDeleteTool, useToggleTool } from '../hooks/use-tools'
import { ToolList } from './tool-list'
import { ToolStats } from './tool-stats'
import { ToolFormModal } from './tool-form-modal'
import type { ToolInfo, CreateToolInput, UpdateToolInput } from '../types/tools'
import styles from './tools-panel.module.css'

/** 每页条数 */
const PAGE_SIZE = 5

/** 工具管理面板 */
export default function ToolsPanel() {
  const [page, setPage] = useState(1)
  const { toolsWithStats, total, isLoading, summary, isSummaryLoading, refetch } = useTools({ page, pageSize: PAGE_SIZE })
  const createMut = useCreateTool()
  const updateMut = useUpdateTool()
  const deleteMut = useDeleteTool()
  const toggleMut = useToggleTool()

  const [modalOpen, setModalOpen] = useState(false)
  const [editingTool, setEditingTool] = useState<ToolInfo | null>(null)

  const handleCreate = () => {
    setEditingTool(null)
    setModalOpen(true)
  }

  const handleEdit = (tool: ToolInfo) => {
    setEditingTool(tool)
    setModalOpen(true)
  }

  const handleSubmit = (values: CreateToolInput | UpdateToolInput) => {
    if (editingTool) {
      updateMut.mutate(
        { id: editingTool.id, input: values as UpdateToolInput },
        { onSuccess: () => setModalOpen(false) },
      )
    } else {
      createMut.mutate(values as CreateToolInput, {
        onSuccess: () => setModalOpen(false),
      })
    }
  }

  return (
    <div className={styles.panel}>
      <PageHeader
        title="🔌 工具管理"
        description="注册、配置和监控 Agent 工具"
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} loading={isLoading} onClick={refetch}>
              刷新
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              新增工具
            </Button>
          </Space>
        }
      />
      <ToolStats summary={summary} loading={isSummaryLoading} />
      <ToolList
        tools={toolsWithStats}
        total={total}
        page={page}
        pageSize={PAGE_SIZE}
        loading={isLoading}
        onEdit={handleEdit}
        onDelete={(id) => deleteMut.mutate(id)}
        onToggle={(id, enable) => toggleMut.mutate({ id, enable })}
        onPageChange={setPage}
      />
      <ToolFormModal
        open={modalOpen}
        tool={editingTool}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        confirmLoading={createMut.isPending || updateMut.isPending}
      />
    </div>
  )
}
