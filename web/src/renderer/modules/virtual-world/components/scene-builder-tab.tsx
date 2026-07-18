import { useState } from 'react'
import { Button, Select, InputNumber, message, Empty } from 'antd'
import {
  PlusOutlined,
  DeleteOutlined,
  BuildOutlined,
  AimOutlined,
} from '@ant-design/icons'
import {
  useScenes,
  useSceneBlocks,
  usePlaceBlock,
  useRemoveBlock,
  useBlocks,
} from '../hooks/use-virtual-world'
import styles from '../virtual-world-panel.module.css'

const GEOMETRY_ICONS: Record<string, string> = {
  box: '▣', cylinder: '●', sphere: '○', cone: '△', plane: '▬',
}

export default function SceneBuilderTab() {
  const [selectedScene, setSelectedScene] = useState<number | null>(null)
  const [selectedBlock, setSelectedBlock] = useState<string>('')
  const [posX, setPosX] = useState(0)
  const [posY, setPosY] = useState(0)
  const [posZ, setPosZ] = useState(0)
  const [rotationY, setRotationY] = useState(0)

  const { data: scenesData } = useScenes()
  const { data: blocksData } = useBlocks()
  const { data: sceneBlocks } = useSceneBlocks(selectedScene)
  const placeBlock = usePlaceBlock(selectedScene ?? 0)
  const removeBlock = useRemoveBlock(selectedScene ?? 0)

  const handlePlace = async () => {
    if (!selectedScene || !selectedBlock) { message.warning('请先选择场景和方块'); return }
    try {
      await placeBlock.mutateAsync({ blockId: selectedBlock, posX, posY, posZ, rotationY })
      message.success(`已放置 ${selectedBlock} → (${posX}, ${posY}, ${posZ})`)
    } catch {
      message.error('放置失败')
    }
  }

  const handleRemove = async (x: number, y: number, z: number) => {
    if (!selectedScene) return
    try {
      await removeBlock.mutateAsync({ x, y, z })
      message.success('已移除')
    } catch {
      message.error('移除失败')
    }
  }

  const blocks = sceneBlocks ?? []

  return (
    <div className={styles.panel}>
      <div className={styles.builderLayout}>
        {/* ═══ 左侧：放置面板 + 方块列表 ═══ */}
        <div>
          {/* 放置工具栏 */}
          <div className={styles.formCard}>
            <div className={styles.cardHeader}>
              <div className={styles.cardIconOrange}>
                <AimOutlined />
              </div>
              <span className={styles.cardTitle}>放置方块</span>
            </div>

            <div className={styles.builderForm}>
              <div className={styles.formRow}>
                <span className={styles.formLabel}>场景</span>
                <Select
                  placeholder="选择场景"
                  className={styles.sceneSelect}
                  value={selectedScene}
                  onChange={setSelectedScene}
                  options={scenesData?.items?.map((s) => ({
                    label: `${s.name}${s.isActive ? ' ✓' : ''}`,
                    value: s.id,
                  })) ?? []}
                />
              </div>

              <div className={styles.formRow}>
                <span className={styles.formLabel}>方块</span>
                <Select
                  placeholder="选择方块类型"
                  className={styles.blockSelect}
                  value={selectedBlock || undefined}
                  onChange={setSelectedBlock}
                  options={blocksData?.items?.map((b) => ({
                    label: `${GEOMETRY_ICONS[b.geometryType] ?? '□'} ${b.name} (${b.blockId})`,
                    value: b.blockId,
                  })) ?? []}
                />
              </div>

              <div className={styles.formRow}>
                <span className={styles.formLabel}>坐标</span>
                <InputNumber
                  placeholder="X"
                  value={posX}
                  onChange={(v) => setPosX(v ?? 0)}
                  className={styles.coordInput}
                  controls={false}
                />
                <InputNumber
                  placeholder="Y"
                  value={posY}
                  onChange={(v) => setPosY(v ?? 0)}
                  className={styles.coordInput}
                  controls={false}
                />
                <InputNumber
                  placeholder="Z"
                  value={posZ}
                  onChange={(v) => setPosZ(v ?? 0)}
                  className={styles.coordInput}
                  controls={false}
                />
                <Select
                  value={rotationY}
                  onChange={setRotationY}
                  className={styles.rotationSelect}
                  options={[
                    { label: '0°', value: 0 },
                    { label: '90°', value: 90 },
                    { label: '180°', value: 180 },
                    { label: '270°', value: 270 },
                  ]}
                />
                <Button
                  className={styles.btnPrimary}
                  icon={<PlusOutlined />}
                  onClick={handlePlace}
                  disabled={!selectedScene || !selectedBlock}
                >
                  放置
                </Button>
              </div>
            </div>
          </div>

          {/* 已放置方块列表 */}
          <div className={styles.blockListPanel}>
            <div className={styles.blockListHeader}>
              <span className={styles.blockListTitle}>已放置方块</span>
              <span className={styles.blockListCount}>{blocks.length}</span>
            </div>
            <div className={styles.blockListBody}>
              {blocks.length === 0 ? (
                <div className={styles.blockListEmpty}>
                  <Empty
                    image={Empty.PRESENTED_IMAGE_SIMPLE}
                    description={
                      <span className={styles.blockListEmptyText}>
                        {selectedScene ? '还没有放置方块' : '请先选择一个场景'}
                      </span>
                    }
                  />
                </div>
              ) : (
                blocks.map((b) => (
                  <div key={b.id} className={styles.blockListItem}>
                    <div className={styles.blockListItemLeft}>
                      <div className={styles.blockListItemIcon}>
                        {GEOMETRY_ICONS[b.blockId] ?? '□'}
                      </div>
                      <div className={styles.blockListItemInfo}>
                        <span className={styles.blockListItemName}>{b.blockId}</span>
                        <span className={styles.blockListItemPos}>
                          ({b.posX}, {b.posY}, {b.posZ})
                          {b.rotationY !== 0 && ` · ${b.rotationY}°`}
                          {b.material && ` · ${b.material}`}
                        </span>
                      </div>
                    </div>
                    <Button
                      type="text"
                      danger
                      icon={<DeleteOutlined />}
                      size="small"
                      onClick={() => handleRemove(b.posX, b.posY, b.posZ)}
                      className={styles.deleteBtn}
                    />
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* ═══ 右侧：场景预览 ═══ */}
        <div>
          <div className={styles.card}>
            <div className={styles.cardHeader}>
              <div className={styles.cardIconBlue}>
                <BuildOutlined />
              </div>
              <span className={styles.cardTitle}>场景概览</span>
            </div>
            {selectedScene ? (
              <div className={styles.infoGrid}>
                <div className={styles.infoItem}>
                  <span className={styles.infoLabel}>已选场景</span>
                  <span className={styles.infoValue}>
                    {scenesData?.items?.find((s) => s.id === selectedScene)?.name ?? '—'}
                  </span>
                </div>
                <div className={styles.infoItem}>
                  <span className={styles.infoLabel}>方块数</span>
                  <span className={styles.infoValue}>{blocks.length}</span>
                </div>
                <div className={styles.infoItem}>
                  <span className={styles.infoLabel}>方块类型</span>
                  <span className={styles.infoValue}>
                    {new Set(blocks.map((b) => b.blockId)).size} 种
                  </span>
                </div>
              </div>
            ) : (
              <div className={styles.builderEmptyWrap}>
                <BuildOutlined className={styles.emptyIcon} />
                <div className={styles.emptyText}>选择一个场景开始搭建</div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
