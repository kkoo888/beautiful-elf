import { Button, message, Popconfirm, Empty } from 'antd'
import { PlusOutlined, DeleteOutlined, BlockOutlined } from '@ant-design/icons'
import { useBlocks, useDeleteBlock } from '../hooks/use-virtual-world'
import type { VirtualWorldBlock } from '../types'
import styles from '../virtual-world-panel.module.css'

const CATEGORY_STYLES: Record<string, { label: string; cls: string }> = {
  structure: { label: '结构', cls: styles.catStructure },
  decoration: { label: '装饰', cls: styles.catDecoration },
  nature: { label: '自然', cls: styles.catNature },
  furniture: { label: '家具', cls: styles.catFurniture },
  light: { label: '灯光', cls: styles.catLight },
  road: { label: '道路', cls: styles.catRoad },
}

const GEOMETRY_ICONS: Record<string, string> = {
  box: '▣',
  cylinder: '●',
  sphere: '○',
  cone: '△',
  plane: '▬',
  dodecahedron: '◈',
}

export default function BlockRegistryTab() {
  const { data: blocksData, isLoading } = useBlocks()
  const deleteBlock = useDeleteBlock()

  const handleDelete = async (id: number) => {
    try {
      await deleteBlock.mutateAsync(id)
      message.success('已删除')
    } catch {
      message.error('删除失败')
    }
  }

  const blocks = blocksData?.items ?? []

  return (
    <div className={styles.panel}>
      {/* 工具栏 */}
      <div className={styles.toolbar}>
        <div className={styles.toolbarLeft}>
          <span className={styles.toolbarTitle}>方块库</span>
          <span className={styles.toolbarCount}>{blocks.length} 种方块</span>
        </div>
        <Button className={styles.btnPrimary} icon={<PlusOutlined />} size="small">
          注册新方块
        </Button>
      </div>

      {/* 方块网格 */}
      {blocks.length === 0 ? (
        <div className={styles.emptyWrap}>
          <BlockOutlined className={styles.emptyIcon} />
          <div className={styles.emptyText}>
            还没有注册方块<br />
            点击上方按钮注册第一个方块类型
          </div>
        </div>
      ) : (
        <div className={styles.blockGrid}>
          {blocks.map((block) => {
            const cat = CATEGORY_STYLES[block.category] ?? { label: block.category, cls: '' }
            return (
              <div key={block.id} className={styles.blockCard}>
                <div className={styles.blockCardHeader}>
                  <span className={styles.blockId}>{block.blockId}</span>
                  <Popconfirm
                    title="确认删除此方块类型？"
                    onConfirm={() => handleDelete(block.id)}
                    okText="删除"
                    cancelText="取消"
                  >
                    <Button
                      type="text"
                      danger
                      icon={<DeleteOutlined />}
                      size="small"
                      className={styles.deleteBtn}
                    />
                  </Popconfirm>
                </div>

                <div className={styles.blockMeta}>
                  <div className={styles.blockMetaRow}>
                    <span>{block.name}</span>
                    <span className={cat.cls}>{cat.label}</span>
                  </div>
                  <div className={styles.blockMetaRow}>
                    <span>{GEOMETRY_ICONS[block.geometryType] ?? '□'} {block.geometryType}</span>
                    <span>·</span>
                    <span>{block.defaultMaterial}</span>
                  </div>
                </div>

                {block.description && (
                  <div className={styles.blockDesc}>{block.description}</div>
                )}

                {block.tags && (
                  <div className={styles.blockTags}>
                    {block.tags.split(',').filter(Boolean).map((tag) => (
                      <span key={tag} className={styles.blockTag}>{tag.trim()}</span>
                    ))}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
