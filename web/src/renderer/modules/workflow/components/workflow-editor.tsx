/** DAG 编辑器（简化版：步骤列表拖拽排序） */

import { List, Tag, Button, Space, Typography, Input } from 'antd'
import { HolderOutlined, PlusOutlined, DeleteOutlined } from '@ant-design/icons'
import { useState, useCallback } from 'react'
import type { WorkflowStep } from '../types/workflow'
import { generateId } from '@/utils'
import styles from './workflow-panel.module.css'

const { Text } = Typography

const STEP_TYPE_MAP: Record<WorkflowStep['type'], { label: string; color: string }> = {
  action: { label: '动作', color: 'blue' },
  condition: { label: '条件', color: 'orange' },
  loop: { label: '循环', color: 'purple' },
  parallel: { label: '并行', color: 'cyan' },
}

interface WorkflowEditorProps {
  /** 初始步骤列表 */
  steps: WorkflowStep[]
  /** 步骤变更回调 */
  onStepsChange: (steps: WorkflowStep[]) => void
  /** 是否只读 */
  readonly?: boolean
}

export function WorkflowEditor({ steps, onStepsChange, readonly }: WorkflowEditorProps) {
  const [newStepName, setNewStepName] = useState('')
  const [dragIndex, setDragIndex] = useState<number | null>(null)

  const handleDragStart = useCallback((index: number) => {
    setDragIndex(index)
  }, [])

  const handleDragOver = useCallback(
    (e: React.DragEvent, index: number) => {
      e.preventDefault()
      if (dragIndex === null || dragIndex === index) return
      const reordered = [...steps]
      const [moved] = reordered.splice(dragIndex, 1)
      reordered.splice(index, 0, moved)
      const updated = reordered.map((s, i) => ({ ...s, order: i }))
      onStepsChange(updated)
      setDragIndex(index)
    },
    [dragIndex, steps, onStepsChange]
  )

  const handleDragEnd = useCallback(() => {
    setDragIndex(null)
  }, [])

  const handleAddStep = useCallback(() => {
    if (!newStepName.trim()) return
    const newStep: WorkflowStep = {
      id: generateId(),
      name: newStepName.trim(),
      type: 'action',
      config: {},
      dependsOn: [],
      order: steps.length,
    }
    onStepsChange([...steps, newStep])
    setNewStepName('')
  }, [newStepName, steps, onStepsChange])

  const handleRemoveStep = useCallback(
    (id: string) => {
      const filtered = steps.filter((s) => s.id !== id).map((s, i) => ({ ...s, order: i }))
      onStepsChange(filtered)
    },
    [steps, onStepsChange]
  )

  return (
    <div>
      <div className={styles.stepList}>
        <List
          dataSource={steps}
          renderItem={(step, index) => (
            <div
              className={styles.stepItem}
              draggable={!readonly}
              onDragStart={() => handleDragStart(index)}
              onDragOver={(e) => handleDragOver(e, index)}
              onDragEnd={handleDragEnd}
              style={{ opacity: dragIndex === index ? 0.5 : 1 }}
            >
              {!readonly && (
                <div className={styles.dragHandle}>
                  <HolderOutlined />
                </div>
              )}
              <div className={styles.stepIndex}>{index + 1}</div>
              <div className={styles.stepInfo}>
                <div className={styles.stepName}>{step.name}</div>
                <div className={styles.stepType}>
                  <Tag color={STEP_TYPE_MAP[step.type].color}>{STEP_TYPE_MAP[step.type].label}</Tag>
                </div>
              </div>
              {!readonly && (
                <Button
                  type="text"
                  size="small"
                  danger
                  icon={<DeleteOutlined />}
                  onClick={() => handleRemoveStep(step.id)}
                />
              )}
            </div>
          )}
          locale={{ emptyText: <Text type="secondary">暂无步骤，添加一个开始编排</Text> }}
        />
      </div>
      {!readonly && (
        <Space.Compact style={{ marginTop: 12 }}>
          <Input
            placeholder="输入步骤名称"
            value={newStepName}
            onChange={(e) => setNewStepName(e.target.value)}
            onPressEnter={handleAddStep}
            style={{ width: 240 }}
          />
          <Button type="primary" icon={<PlusOutlined />} onClick={handleAddStep}>
            添加步骤
          </Button>
        </Space.Compact>
      )}
    </div>
  )
}
