import { useEffect, useState, useCallback } from 'react'
import { Button, Switch, Typography, message } from 'antd'
import { API_BASE_URL, API_PREFIX } from '@shared/constants'
import {
  ReloadOutlined,
  SyncOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  ZoomInOutlined,
  ZoomOutOutlined,
  UndoOutlined,
  CameraOutlined,
} from '@ant-design/icons'
import { useElectronApi } from '@/hooks'
import { apiClient, extractData } from '@/services/api-client'
import { loadPetModelPath, loadPetSettings } from '../services/pet-api'
import PetScreenshotPreview from './pet-screenshot-preview'
import styles from '../pet-panel.module.css'

/** 获取模型文件名 */
function getModelName(path: string | null): string {
  if (!path) return '—'
  return path.split('/').pop() || path.split('\\').pop() || path
}

export default function PetControlTab() {
  const { pet: petApi, isElectron } = useElectronApi()

  const [petActive, setPetActive] = useState(false)
  const [petWindowVisible, setPetWindowVisible] = useState(false)
  const [modelName, setModelName] = useState<string>('—')
  const [modelPath, setModelPath] = useState<string | null>(null)
  const [screenshot, setScreenshot] = useState<string | null>(null)
  const [idleOn, setIdleOn] = useState(true)
  const [bgImage, setBgImage] = useState<string>('')

  // ── 订阅可见性变化 ──
  useEffect(() => {
    if (!isElectron) return
    const cleanup = petApi.onVisibilityChange((visible: boolean) => {
      setPetWindowVisible(visible)
      if (visible) setPetActive(true)
    })
    return () => cleanup()
  }, [isElectron, petApi])

  useEffect(() => {
    petApi.isVisible().then((result) => {
      if (result.success) setPetWindowVisible(result.visible)
    })
  }, [])

  // ── 手动截图（点击按钮触发 pet 窗口上传截图到后端）──
  const handleScreenshot = useCallback(async () => {
    if (!isElectron) { message.warning('当前环境不支持宠物窗口'); return }
    petApi.requestScreenshot()
    // 等 1s 让 pet 窗口完成上传，再通过 API URL 显示（对齐 image_gallery/files 模式）
    setTimeout(() => {
      const url = `${API_BASE_URL}${API_PREFIX}/pets/screenshot/latest?t=${Date.now()}`
      setScreenshot(url)
    }, 1000)
  }, [isElectron, petApi])

  // ── 品牌背景图 ──
  useEffect(() => {
    apiClient
      .get('/configs/branding.background_image')
      .then((res) => {
        const data = extractData(res) as { keyValue?: string }
        if (data?.keyValue) setBgImage(`${window.location.origin}/${data.keyValue}`)
      })
      .catch(() => {})
  }, [])

  // ── 加载模型信息 ──
  useEffect(() => {
    void (async () => {
      try {
        const [settings, directPath] = await Promise.all([loadPetSettings(), loadPetModelPath()])
        const path = (settings?.modelPath as string) ?? directPath ?? null
        setModelPath(path)
        setModelName(getModelName(path))
      } catch {
        setModelName('—')
      }
    })()
  }, [])

  // ── 模型切换通知 ──
  useEffect(() => {
    if (!isElectron) return
    const cleanup = petApi.onModelChanged(() => {
      void (async () => {
        try {
          const [settings, directPath] = await Promise.all([loadPetSettings(), loadPetModelPath()])
          const path = (settings?.modelPath as string) ?? directPath ?? null
          setModelPath(path)
          setModelName(getModelName(path))
        } catch {
          setModelName('—')
        }
      })()
    })
    return () => cleanup()
  }, [isElectron, petApi])

  // ── 操作回调 ──
  const handleTogglePet = useCallback(async () => {
    if (!isElectron) { message.warning('当前环境不支持宠物窗口'); return }
    const result = await petApi.toggle()
    if (result.success) {
      message.success(result.visible ? '宠物窗口已显示' : '宠物窗口已隐藏')
      setPetWindowVisible(result.visible)
    }
  }, [isElectron, petApi])

  const handleRefresh = useCallback(async () => {
    if (!isElectron) { message.warning('当前环境不支持宠物窗口'); return }
    message.info('正在刷新场景...')
    const result = await petApi.reload()
    if (!result.success) message.error(result.message || '刷新失败')
  }, [isElectron, petApi])

  const handleZoom = useCallback(
    async (factor: number) => {
      if (!isElectron) { message.warning('当前环境不支持宠物窗口'); return }
      const result = await petApi.zoom(factor)
      if (!result.success) message.error(result.message || '缩放失败')
    },
    [isElectron, petApi],
  )

  const handleResetZoom = useCallback(async () => {
    if (!isElectron) { message.warning('当前环境不支持宠物窗口'); return }
    const result = await petApi.resetZoom()
    if (!result.success) message.error(result.message || '重置失败')
  }, [isElectron, petApi])

  const handleToggleIdle = useCallback(
    async (checked: boolean) => {
      setIdleOn(checked)
      if (!isElectron) { message.warning('当前环境不支持宠物窗口'); return }
      const result = await petApi.setIdle(checked)
      if (!result.success) message.error(result.message || '设置失败')
    },
    [isElectron, petApi],
  )

  // ── 渲染 ──
  return (
    <div className={styles.panel}>
      <div className={styles.mainLayout}>
        {/* ═══ 左侧：截图预览 ═══ */}
        <div className={styles.previewSide}>
          <div
            className={styles.previewWrap}
            style={
              bgImage
                ? { background: `url(${bgImage}) center/cover no-repeat` }
                : undefined
            }
          >
            <PetScreenshotPreview
              screenshot={screenshot}
              petVisible={petWindowVisible}
              onClick={handleTogglePet}
            />
          </div>

          {/* 预览区下方：状态指示 */}
          <div className={styles.statusRow}>
            <div className={styles.statusItem}>
              <span className={petActive ? styles.statusDotActive : styles.statusDotInactive} />
              <span>{petActive ? '已启动' : '未启动'}</span>
            </div>
            <div className={styles.statusItem}>
              <span className={petWindowVisible ? styles.statusDotActive : styles.statusDotInactive} />
              <span>桌面窗口 {petWindowVisible ? '显示中' : '已隐藏'}</span>
            </div>
          </div>
        </div>

        {/* ═══ 右侧：控制区 ═══ */}
        <div className={styles.controlSide}>
          {/* ── 主操作 ── */}
          <div className={styles.card}>
            <div className={styles.actionRow}>
              <Button
                className={petWindowVisible ? styles.actionBtn : styles.actionBtnPrimary}
                icon={petWindowVisible ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
                onClick={handleTogglePet}
              >
                {petWindowVisible ? '隐藏宠物' : '显示宠物'}
              </Button>
              <Button className={styles.actionBtn} icon={<SyncOutlined />} onClick={handleRefresh}>
                刷新场景
              </Button>
              <Button className={styles.actionBtn} icon={<ReloadOutlined />} onClick={handleRefresh}>
                重载模型
              </Button>
              <Button className={styles.actionBtn} icon={<CameraOutlined />} onClick={handleScreenshot}>
                截图
              </Button>
            </div>
          </div>

          {/* ── 交互控制 ── */}
          <div className={styles.card}>
            <div className={styles.cardTitle}>交互控制</div>

            {/* 缩放 */}
            <div className={styles.zoomRow}>
              <span className={styles.zoomLabel}>缩放</span>
              <div className={styles.zoomBtnGroup}>
                <Button className={styles.zoomBtn} icon={<ZoomInOutlined />} onClick={() => handleZoom(1.15)} />
                <Button className={styles.zoomBtn} icon={<ZoomOutOutlined />} onClick={() => handleZoom(1 / 1.15)} />
                <Button className={styles.zoomBtn} icon={<UndoOutlined />} onClick={handleResetZoom} />
              </div>
            </div>

            {/* 待机动作 */}
            <div className={styles.idleRow} style={{ marginTop: 10 }}>
              <span className={styles.idleLabel}>待机动作</span>
              <Switch
                size="small"
                checked={idleOn}
                onChange={handleToggleIdle}
                checkedChildren="开"
                unCheckedChildren="关"
              />
            </div>
          </div>

          {/* ── 模型信息 ── */}
          <div className={styles.card}>
            <div className={styles.cardTitle}>模型信息</div>
            <div className={styles.modelInfo}>
              <div className={styles.modelRow}>
                <span className={styles.modelLabel}>名称</span>
                <span className={styles.modelValue}>{modelName}</span>
              </div>
              <div className={styles.modelRow}>
                <span className={styles.modelLabel}>状态</span>
                <span className={styles.modelValue}>{modelPath ? '已加载' : '未配置'}</span>
              </div>
              <div className={styles.modelRow}>
                <span className={styles.modelLabel}>引擎</span>
                <span className={styles.modelValue}>Three.js + MMD</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
