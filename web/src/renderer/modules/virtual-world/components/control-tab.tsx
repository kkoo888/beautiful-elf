import { useState, useCallback } from 'react'
import { Button, message } from 'antd'
import {
  ControlOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  ReloadOutlined,
  CameraOutlined,
  PlusOutlined,
  EnvironmentOutlined,
  BgColorsOutlined,
  ClockCircleOutlined,
  AppstoreOutlined,
} from '@ant-design/icons'
import { useElectronApi } from '@/hooks'
import { API_BASE_URL, API_PREFIX } from '@shared/constants'
import { useScenes, useActivateScene, useCreateScene } from '../hooks/use-virtual-world'
import { placeBlock } from '../services/virtual-world-api'
import styles from '../virtual-world-panel.module.css'

export default function ControlTab() {
  const { world: worldApi, isElectron } = useElectronApi()
  const [worldVisible, setWorldVisible] = useState(false)
  const [screenshot, setScreenshot] = useState<string | null>(null)

  const { data: scenesData } = useScenes()
  const activateScene = useActivateScene()
  const createScene = useCreateScene()

  const activeScene = scenesData?.items?.find((s) => s.isActive)

  const handleToggleWorld = useCallback(async () => {
    if (!isElectron) { message.warning('请在桌面端使用'); return }
    const result = await worldApi.toggle()
    if (result.success) {
      message.success(result.visible ? '世界已展开' : '世界已收起')
      setWorldVisible(result.visible)
    }
  }, [isElectron, worldApi])

  const handleReload = useCallback(async () => {
    if (!isElectron) { message.warning('请在桌面端使用'); return }
    message.info('重载中...')
    const result = await worldApi.reload()
    if (!result.success) message.error(result.message || '重载失败')
  }, [isElectron, worldApi])

  const handleScreenshot = useCallback(async () => {
    if (!isElectron) { message.warning('请在桌面端使用'); return }
    worldApi.requestScreenshot()
    setTimeout(() => {
      setScreenshot(`${API_BASE_URL}${API_PREFIX}/virtualworld/screenshot/latest?t=${Date.now()}`)
    }, 1000)
  }, [isElectron, worldApi])

  const handleCreateDefault = useCallback(async () => {
    try {
      // 1. 创建场景
      const scene = await createScene.mutateAsync({
        name: '默认世界',
        description: '默认虚拟世界场景',
        width: 32,
        depth: 32,
        height: 16,
      })

      // 2. 激活场景
      await activateScene.mutateAsync(scene.id)

      // 3. 放置默认方块（地板 + 围墙 + 装饰）
      const sceneId = scene.id
      const blocks = [
        // 地板（5x5）
        ...Array.from({ length: 5 }, (_, x) =>
          Array.from({ length: 5 }, (_, z) => ({ blockId: 'floor', posX: x, posY: 0, posZ: z }))
        ).flat(),
        // 围墙（墙高3，中心在Y=1.5，底部在地板上）
        ...Array.from({ length: 5 }, (_, x) => [
          { blockId: 'wall', posX: x, posY: 1.5, posZ: 0 },
          { blockId: 'wall', posX: x, posY: 1.5, posZ: 4 },
        ]).flat(),
        ...Array.from({ length: 3 }, (_, z) => [
          { blockId: 'wall', posX: 0, posY: 1.5, posZ: z + 1 },
          { blockId: 'wall', posX: 4, posY: 1.5, posZ: z + 1 },
        ]).flat(),
        // 屋顶（在墙顶）
        ...Array.from({ length: 5 }, (_, x) =>
          Array.from({ length: 5 }, (_, z) => ({ blockId: 'roof_flat', posX: x, posY: 3, posZ: z }))
        ).flat(),
        // 柱子（高3，中心在Y=1.5）
        { blockId: 'pillar', posX: 0, posY: 1.5, posZ: 0 },
        { blockId: 'pillar', posX: 4, posY: 1.5, posZ: 0 },
        { blockId: 'pillar', posX: 0, posY: 1.5, posZ: 4 },
        { blockId: 'pillar', posX: 4, posY: 1.5, posZ: 4 },
        // 装饰（树干高2，中心在Y=1）
        { blockId: 'tree_trunk', posX: -2, posY: 1, posZ: 2 },
        { blockId: 'tree_canopy', posX: -2, posY: 2.5, posZ: 2 },
        { blockId: 'flower', posX: -1, posY: 0.15, posZ: 3 },
        { blockId: 'flower', posX: 6, posY: 0.15, posZ: 1 },
        { blockId: 'rock', posX: 6, posY: 0.15, posZ: 3 },
      ]

      // 批量放置方块
      for (const b of blocks) {
        try {
          await placeBlock(sceneId, {
            blockId: b.blockId,
            posX: b.posX,
            posY: b.posY,
            posZ: b.posZ,
          })
        } catch {
          // 忽略单个方块失败
        }
      }

      message.success(`默认世界已创建 (${blocks.length} 个方块)`)

      // 4. 重载渲染窗口
      worldApi.reload()
    } catch {
      message.error('创建失败')
    }
  }, [createScene, activateScene, worldApi])

  return (
    <div className={styles.panel}>
      <div className={styles.controlLayout}>
        {/* ═══ 左侧：场景预览 ═══ */}
        <div className={styles.scenePreview}>
          <div className={styles.previewFrame}>
            {screenshot ? (
              <img src={screenshot} alt="场景预览" className={styles.previewImg} />
            ) : (
              <div className={styles.previewPlaceholder}>
                <EnvironmentOutlined className={styles.previewPlaceholderIcon} />
                <span className={styles.previewPlaceholderText}>
                  点击「展开世界」启动 3D 渲染
                </span>
              </div>
            )}
          </div>

          <div className={styles.statusBar}>
            <div className={styles.statusChip}>
              <span className={worldVisible ? styles.dotActive : styles.dotInactive} />
              3D 窗口 {worldVisible ? '运行中' : '未启动'}
            </div>
            <div className={styles.statusChip}>
              <span className={activeScene ? styles.dotActive : styles.dotInactive} />
              场景: {activeScene?.name ?? '未创建'}
            </div>
          </div>
        </div>

        {/* ═══ 右侧：控制卡片 ═══ */}
        <div className={styles.controlStack}>
          {/* 世界控制 */}
          <div className={styles.card}>
            <div className={styles.cardHeader}>
              <div className={styles.cardIconOrange}>
                <ControlOutlined />
              </div>
              <span className={styles.cardTitle}>世界控制</span>
            </div>
            <div className={styles.btnRow}>
              <Button
                className={worldVisible ? styles.btnSecondary : styles.btnPrimary}
                icon={worldVisible ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
                onClick={handleToggleWorld}
              >
                {worldVisible ? '收起世界' : '展开世界'}
              </Button>
              <Button className={styles.btnSecondary} icon={<ReloadOutlined />} onClick={handleReload}>
                重载
              </Button>
              <Button className={styles.btnSecondary} icon={<CameraOutlined />} onClick={handleScreenshot}>
                截图
              </Button>
            </div>
          </div>

          {/* 场景管理 */}
          <div className={styles.card}>
            <div className={styles.cardHeader}>
              <div className={styles.cardIconBlue}>
                <EnvironmentOutlined />
              </div>
              <span className={styles.cardTitle}>场景管理</span>
            </div>
            <div className={activeScene ? styles.btnRowHasScene : styles.btnRow}>
              <Button className={styles.btnSecondary} icon={<PlusOutlined />} onClick={handleCreateDefault}>
                创建默认世界
              </Button>
            </div>
            {activeScene && (
              <div className={styles.infoGrid}>
                <div className={styles.infoItem}>
                  <span className={styles.infoLabel}>名称</span>
                  <span className={styles.infoValue}>{activeScene.name}</span>
                </div>
                <div className={styles.infoItem}>
                  <span className={styles.infoLabel}>尺寸</span>
                  <span className={styles.infoValue}>
                    {activeScene.width}×{activeScene.depth}×{activeScene.height}
                  </span>
                </div>
                <div className={styles.infoItem}>
                  <span className={styles.infoLabel}>
                    <ClockCircleOutlined className={styles.infoIcon} />
                    时间
                  </span>
                  <span className={styles.infoValue}>{activeScene.timeOfDay}:00</span>
                </div>
                <div className={styles.infoItem}>
                  <span className={styles.infoLabel}>
                    <BgColorsOutlined className={styles.infoIcon} />
                    环境光
                  </span>
                  <span className={styles.infoValue}>
                    <span className={styles.colorSwatch}>
                      <span
                        className={styles.colorDot}
                        style={{ background: activeScene.ambientColor }}
                      />
                      {activeScene.ambientColor}
                    </span>
                  </span>
                </div>
                <div className={styles.infoItem}>
                  <span className={styles.infoLabel}>天空色</span>
                  <span className={styles.infoValue}>
                    <span className={styles.colorSwatch}>
                      <span
                        className={styles.colorDot}
                        style={{ background: activeScene.skyColor }}
                      />
                      {activeScene.skyColor}
                    </span>
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* 场景统计 */}
          <div className={styles.card}>
            <div className={styles.cardHeader}>
              <div className={styles.cardIconGreen}>
                <AppstoreOutlined />
              </div>
              <span className={styles.cardTitle}>场景统计</span>
            </div>
            <div className={styles.infoGrid}>
              <div className={styles.infoItem}>
                <span className={styles.infoLabel}>方块总数</span>
                <span className={styles.infoValue}>—</span>
              </div>
              <div className={styles.infoItem}>
                <span className={styles.infoLabel}>场景数量</span>
                <span className={styles.infoValue}>{scenesData?.total ?? 0}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
