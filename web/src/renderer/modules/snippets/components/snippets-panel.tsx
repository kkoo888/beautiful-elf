import { useState, useCallback, useMemo } from 'react'
import { Typography, Button, Drawer, Space, Spin, message } from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import { SnippetCard } from './snippet-card'
import { SnippetForm } from './snippet-form'
import { SnippetSearch } from './snippet-search'
import {
  useSnippets,
  useSnippetTags,
  useCreateSnippet,
  useUpdateSnippet,
  useDeleteSnippet,
  useRecordSnippetUse,
} from '../hooks/use-snippets'
import type { Snippet, SnippetFormData, SnippetQueryParams } from '../types/snippets'
import styles from './snippets-panel.module.css'

const { Title, Text } = Typography

export function SnippetsPanel() {
  // 搜索 / 筛选状态
  const [keyword, setKeyword] = useState('')
  const [selectedTags, setSelectedTags] = useState<string[]>([])

  // Drawer 状态
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [editingSnippet, setEditingSnippet] = useState<Snippet | null>(null)

  // 查询参数
  const queryParams = useMemo<SnippetQueryParams>(
    () => ({
      keyword: keyword || undefined,
      tags: selectedTags.length > 0 ? selectedTags : undefined,
    }),
    [keyword, selectedTags]
  )

  // 数据查询
  const { data, isLoading } = useSnippets(queryParams)
  const { data: allTags = [] } = useSnippetTags()

  // mutations
  const createMutation = useCreateSnippet()
  const updateMutation = useUpdateSnippet()
  const deleteMutation = useDeleteSnippet()
  const recordUseMutation = useRecordSnippetUse()

  const snippets = data?.items ?? []
  const isSaving = createMutation.isPending || updateMutation.isPending

  // 打开创建
  const handleCreate = useCallback(() => {
    setEditingSnippet(null)
    setDrawerOpen(true)
  }, [])

  // 打开编辑
  const handleEdit = useCallback((snippet: Snippet) => {
    setEditingSnippet(snippet)
    setDrawerOpen(true)
  }, [])

  // 关闭 Drawer
  const handleCloseDrawer = useCallback(() => {
    setDrawerOpen(false)
    setEditingSnippet(null)
  }, [])

  // 提交表单
  const handleSubmit = useCallback(
    (data: SnippetFormData) => {
      if (editingSnippet) {
        updateMutation.mutate({ id: editingSnippet.id, data }, { onSuccess: handleCloseDrawer })
      } else {
        createMutation.mutate(data, { onSuccess: handleCloseDrawer })
      }
    },
    [editingSnippet, createMutation, updateMutation, handleCloseDrawer]
  )

  // 删除
  const handleDelete = useCallback(
    (id: string) => {
      deleteMutation.mutate(id)
    },
    [deleteMutation]
  )

  // 复制代码
  const handleCopy = useCallback(
    (snippet: Snippet) => {
      void navigator.clipboard.writeText(snippet.content)
      recordUseMutation.mutate(snippet.id)
      message.success('代码已复制到剪贴板')
    },
    [recordUseMutation]
  )

  return (
    <div className={styles.panel}>
      {/* 头部 */}
      <div className={styles.panelHeader}>
        <Title level={4} className={styles.panelTitle}>
          💻 代码片段
        </Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
          新建片段
        </Button>
      </div>

      {/* 搜索 */}
      <SnippetSearch
        keyword={keyword}
        onKeywordChange={setKeyword}
        selectedTags={selectedTags}
        onTagsChange={setSelectedTags}
        allTags={allTags}
      />

      {/* 内容区 */}
      {isLoading ? (
        <div className={styles.loadingContainer}>
          <Spin size="large" />
        </div>
      ) : snippets.length === 0 ? (
        <div className={styles.emptyState}>
          <div className={styles.emptyIcon}>💻</div>
          <Text className={styles.emptyText}>暂无代码片段</Text>
          <Text className={styles.emptyHint}>保存你的代码片段，方便快速复用</Text>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={handleCreate}
            style={{ marginTop: 16 }}
          >
            创建第一个片段
          </Button>
        </div>
      ) : (
        <div className={styles.cardGrid}>
          {snippets.map((snippet) => (
            <SnippetCard
              key={snippet.id}
              snippet={snippet}
              onEdit={handleEdit}
              onDelete={handleDelete}
              onCopy={handleCopy}
            />
          ))}
        </div>
      )}

      {/* 创建/编辑 Drawer */}
      <Drawer
        title={editingSnippet ? '编辑片段' : '新建片段'}
        open={drawerOpen}
        onClose={handleCloseDrawer}
        width={680}
        destroyOnClose
        extra={
          <Space>
            <Button onClick={handleCloseDrawer}>取消</Button>
            <Button
              type="primary"
              loading={isSaving}
              onClick={() => {
                // 触发表单提交 - 通过 form 的 id 关联
                document.querySelector<HTMLFormElement>('#snippet-form')?.requestSubmit()
              }}
            >
              {editingSnippet ? '保存' : '创建'}
            </Button>
          </Space>
        }
      >
        <SnippetForm snippet={editingSnippet} onSubmit={handleSubmit} loading={isSaving} />
      </Drawer>
    </div>
  )
}
