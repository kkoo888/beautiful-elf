/** 技能链式配置组件 */

import { useState, useCallback, useRef } from 'react'
import { Button, Empty } from 'antd'
import { HolderOutlined, PlusOutlined, DeleteOutlined } from '@ant-design/icons'
import type { Skill, ChainNode } from '../types/skills'
import styles from './skills-panel.module.css'

interface SkillChainProps {
  skills: Skill[]
  /** 当前链节点（有序） */
  chainNodes: ChainNode[]
  onChange: (nodes: ChainNode[]) => void
}

/** 技能链式配置（拖拽排序） */
export function SkillChain({ skills, chainNodes, onChange }: SkillChainProps) {
  const [dragIndex, setDragIndex] = useState<number | null>(null)
  const [dropIndex, setDropIndex] = useState<number | null>(null)
  const dragOverIndex = useRef<number | null>(null)

  const handleDragStart = useCallback((index: number) => {
    setDragIndex(index)
  }, [])

  const handleDragOver = useCallback((e: React.DragEvent, index: number) => {
    e.preventDefault()
    dragOverIndex.current = index
    setDropIndex(index)
  }, [])

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      if (dragIndex === null || dropIndex === null || dragIndex === dropIndex) {
        setDragIndex(null)
        setDropIndex(null)
        return
      }

      const updated = [...chainNodes]
      const [moved] = updated.splice(dragIndex, 1)
      updated.splice(dropIndex, 0, moved)

      // 重新计算 order
      const reordered = updated.map((node, i) => ({ ...node, order: i }))
      onChange(reordered)
      setDragIndex(null)
      setDropIndex(null)
    },
    [dragIndex, dropIndex, chainNodes, onChange]
  )

  const handleDragEnd = useCallback(() => {
    setDragIndex(null)
    setDropIndex(null)
  }, [])

  const handleAdd = useCallback(
    (skillId: string) => {
      const exists = chainNodes.some((n) => n.skillId === skillId)
      if (exists) return
      const newNode: ChainNode = { skillId, order: chainNodes.length }
      onChange([...chainNodes, newNode])
    },
    [chainNodes, onChange]
  )

  const handleRemove = useCallback(
    (index: number) => {
      const updated = chainNodes
        .filter((_, i) => i !== index)
        .map((node, i) => ({ ...node, order: i }))
      onChange(updated)
    },
    [chainNodes, onChange]
  )

  const getSkillName = (id: string) => skills.find((s) => s.id === id)?.name ?? id

  // 可添加的技能（未在链中的）
  const availableSkills = skills.filter((s) => !chainNodes.some((n) => n.skillId === s.id))

  return (
    <div className={styles.chainContent}>
      {/* 链节点列表 */}
      {chainNodes.length === 0 ? (
        <div className={styles.chainEmpty}>
          <Empty description="拖拽技能到此处配置执行链" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        </div>
      ) : (
        <div className={styles.chainList}>
          {chainNodes.map((node, index) => (
            <div key={node.skillId}>
              <div
                className={`${styles.chainItem} ${
                  dragIndex === index ? styles.chainItemDragging : ''
                } ${dropIndex === index && dragIndex !== null && dragIndex < index ? styles.chainItemDropBelow : ''} ${dropIndex === index && dragIndex !== null && dragIndex > index ? styles.chainItemDropAbove : ''}`}
                draggable
                onDragStart={() => handleDragStart(index)}
                onDragOver={(e) => handleDragOver(e, index)}
                onDrop={handleDrop}
                onDragEnd={handleDragEnd}
              >
                <HolderOutlined className={styles.chainHandle} />
                <span className={styles.chainOrder}>{index + 1}</span>
                <span className={styles.chainName}>{getSkillName(node.skillId)}</span>
                <Button
                  type="text"
                  size="small"
                  danger
                  icon={<DeleteOutlined />}
                  onClick={() => handleRemove(index)}
                />
              </div>
              {index < chainNodes.length - 1 && <div className={styles.chainArrow}>↓</div>}
            </div>
          ))}
        </div>
      )}

      {/* 添加技能到链 */}
      {availableSkills.length > 0 && (
        <div className={styles.detailSection}>
          <span className={styles.detailLabel}>添加技能到链</span>
          <div className={styles.dependencies}>
            {availableSkills.map((s) => (
              <Button
                key={s.id}
                size="small"
                icon={<PlusOutlined />}
                onClick={() => handleAdd(s.id)}
              >
                {s.name}
              </Button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
