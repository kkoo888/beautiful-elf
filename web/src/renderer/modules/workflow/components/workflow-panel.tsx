/** 工作流主面板 - 三栏布局 + 底部监控 */

import { Tabs, Button, Space, Typography, Divider, Input, Empty, Spin, Popconfirm } from 'antd'
import {
  PlusOutlined,
  SaveOutlined,
  PlayCircleOutlined,
  StopOutlined,
  CopyOutlined,
  DeleteOutlined,
} from '@ant-design/icons'
import { useState, useCallback } from 'react'
import { PageHeader } from '@/components/page-header'
import { useWorkflow } from '../hooks/use-workflow'
import { WorkflowEditor } from './workflow-editor'
import { WorkflowTemplates } from './workflow-templates'
import { WorkflowMonitor } from './workflow-monitor'
import { NodePalette } from './node-palette'
import { NodeConfigDrawer } from './node-config-drawer'
import type { WorkflowNode, WorkflowEdge } from '../types/workflow'
import styles from './workflow-panel.module.css'

const { Text } = Typography

/** 工作流模块面板 */
export default function WorkflowPanel() {
  const {
    workflows,
    isLoading,
    runs,
    isRunsLoading,
    templates,
    isTemplatesLoading,
    selectedId,
    setSelectedId,
    activeTab,
    setActiveTab,
    createWorkflowMut,
    deleteWorkflowMut,
    updateWorkflowMut,
    saveDagMut,
    runWorkflowMut,
    stopWorkflowMut,
    duplicateWorkflowMut,
    isMutating,
    selectedWorkflow,
    nodes,
    edges,
    setNodes,
    setEdges,
  } = useWorkflow()

  // 节点配置抽屉
  const [selectedNode, setSelectedNode] = useState<WorkflowNode | null>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)

  // 新建工作流
  const handleCreate = useCallback(async () => {
    const wf = await createWorkflowMut({
      name: '新建工作流',
      description: '',
      triggerType: 'manual',
      nodes: [
        {
          id: 'node-start',
          type: 'start',
          label: '开始',
          position: { x: 250, y: 50 },
          config: {},
          status: 'idle',
        },
        {
          id: 'node-end',
          type: 'end',
          label: '结束',
          position: { x: 250, y: 300 },
          config: {},
          status: 'idle',
        },
      ],
      edges: [],
    })
    setSelectedId(wf.id)
    setActiveTab('editor')
  }, [createWorkflowMut, setSelectedId, setActiveTab])

  // 选择模板
  const handleUseTemplate = useCallback(
    (templateId: string) => {
      // 模板加载到编辑器
      const tpl = templates.find((t) => t.id === templateId)
      if (tpl) {
        void createWorkflowMut({
          name: `${tpl.name}（副本）`,
          description: tpl.description,
          triggerType: 'manual',
          nodes: tpl.nodes.map((n) => ({
            ...n,
            id: `node-${Date.now()}-${n.id}`,
            status: 'idle' as const,
          })),
          edges: tpl.edges.map((e) => ({ ...e, id: `e-${Date.now()}-${e.id}` })),
        }).then((wf) => {
          setSelectedId(wf.id)
          setActiveTab('editor')
        })
      }
    },
    [templates, createWorkflowMut, setSelectedId, setActiveTab]
  )

  // 节点选中 → 打开配置面板
  const handleNodeSelect = useCallback((node: WorkflowNode | null) => {
    if (node) {
      setSelectedNode(node)
      setDrawerOpen(true)
    } else {
      setSelectedNode(null)
      setDrawerOpen(false)
    }
  }, [])

  // 更新节点
  const handleNodeUpdate = useCallback(
    (updatedNode: WorkflowNode) => {
      const newNodes = nodes.map((n) => (n.id === updatedNode.id ? updatedNode : n))
      setNodes(newNodes)
      void saveDagMut(newNodes, edges)
    },
    [nodes, edges, setNodes, saveDagMut]
  )

  // 删除节点
  const handleNodeDelete = useCallback(
    (nodeId: string) => {
      const newNodes = nodes.filter((n) => n.id !== nodeId)
      const newEdges = edges.filter((e) => e.source !== nodeId && e.target !== nodeId)
      setNodes(newNodes)
      setEdges(newEdges)
      void saveDagMut(newNodes, newEdges)
    },
    [nodes, edges, setNodes, setEdges, saveDagMut]
  )

  // 保存 DAG
  const handleSave = useCallback(() => {
    void saveDagMut(nodes, edges)
  }, [nodes, edges, saveDagMut])

  // 左侧栏：工作流列表 + 模板
  const leftPanel = (
    <div className={styles.leftPanel}>
      <div className={styles.leftPanelHeader}>
        <Text strong style={{ fontSize: 14 }}>
          工作流
        </Text>
        <Button
          type="primary"
          size="small"
          icon={<PlusOutlined />}
          onClick={() => void handleCreate()}
        >
          新建
        </Button>
      </div>
      <div className={styles.workflowList}>
        {isLoading ? (
          <Spin style={{ display: 'block', textAlign: 'center', padding: 24 }} />
        ) : workflows.length === 0 ? (
          <Empty description="暂无工作流" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        ) : (
          workflows.map((wf) => (
            <div
              key={wf.id}
              className={`${styles.workflowListItem} ${wf.id === selectedId ? styles.workflowListItemActive : ''}`}
              onClick={() => {
                setSelectedId(wf.id)
                setActiveTab('editor')
              }}
            >
              <div className={styles.workflowListItemName}>{wf.name}</div>
              <div className={styles.workflowListItemDesc}>{wf.description || '无描述'}</div>
            </div>
          ))
        )}
      </div>
      <Divider style={{ margin: '8px 0' }} />
      <NodePalette />
    </div>
  )

  // 中间栏：DAG 编辑器
  const centerPanel = (
    <div className={styles.centerPanel}>
      {selectedWorkflow ? (
        <>
          <div className={styles.editorToolbar}>
            <Space size={8}>
              <Text strong>{selectedWorkflow.name}</Text>
            </Space>
            <Space size={4}>
              <Button
                size="small"
                icon={<SaveOutlined />}
                onClick={handleSave}
                loading={isMutating}
              >
                保存
              </Button>
              <Button
                size="small"
                type="primary"
                icon={<PlayCircleOutlined />}
                onClick={() => void runWorkflowMut(selectedId!)}
                loading={isMutating}
              >
                运行
              </Button>
              <Button
                size="small"
                icon={<StopOutlined />}
                onClick={() => void stopWorkflowMut(selectedId!)}
                loading={isMutating}
              >
                停止
              </Button>
              <Button
                size="small"
                icon={<CopyOutlined />}
                onClick={() => void duplicateWorkflowMut(selectedId!)}
              >
                复制
              </Button>
              <Popconfirm
                title="确定删除此工作流？"
                onConfirm={() =>
                  void deleteWorkflowMut(selectedId!).then(() => setSelectedId(null))
                }
              >
                <Button size="small" danger icon={<DeleteOutlined />} />
              </Popconfirm>
            </Space>
          </div>
          <div className={styles.editorCanvas}>
            <WorkflowEditor
              nodes={nodes}
              edges={edges}
              onNodesChange={setNodes}
              onEdgesChange={setEdges}
              onNodeSelect={handleNodeSelect}
            />
          </div>
        </>
      ) : (
        <div className={styles.editorEmpty}>
          <Empty description="选择左侧工作流或新建一个开始编辑" />
        </div>
      )}
    </div>
  )

  // 底部栏：运行监控
  const bottomPanel = <WorkflowMonitor runs={runs} loading={isRunsLoading} />

  return (
    <div className={styles.panel}>
      <PageHeader title="⚙️ 工作流" description="DAG 工作流编排与运行监控" />
      <div className={styles.mainLayout}>
        {leftPanel}
        <div className={styles.rightSection}>
          {centerPanel}
          <div className={styles.bottomPanel}>
            <Tabs
              size="small"
              items={[{ key: 'monitor', label: '运行监控', children: bottomPanel }]}
            />
          </div>
        </div>
      </div>
      <NodeConfigDrawer
        node={selectedNode}
        open={drawerOpen}
        onClose={() => {
          setDrawerOpen(false)
          setSelectedNode(null)
        }}
        onUpdate={handleNodeUpdate}
        onDelete={handleNodeDelete}
      />
    </div>
  )
}
