import { useEffect, useState, useCallback, useRef } from 'react'
import { Button, Space, Badge, Row, Col, Card, Typography, Switch, message } from 'antd'
import {
  ReloadOutlined,
  SyncOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  ZoomInOutlined,
  ZoomOutOutlined,
} from '@ant-design/icons'
import { useElectronApi } from '@/hooks'
import { apiClient, extractData } from '@/services/api-client'
import { loadPetModelPath, loadPetSettings } from '../services/pet-api'
import PetScreenshotPreview from './pet-screenshot-preview'

const { Text } = Typography

/** 获取模型文件名（去掉路径前缀） */
function getModelName(path: string | null): string {
  if (!path) return '-'
  return path.split('/').pop() || path.split('\\').pop() || path
}

export default function PetControlTab() {
  const { pet: petApi, isElectron } = useElectronApi()

  // 实时状态
  const [petActive, setPetActive] = useState(false)
  const [petWindowVisible, setPetWindowVisible] = useState(false)
  const [modelName, setModelName] = useState<string>('-')
  const [modelPath, setModelPath] = useState<string | null>(null)
  const [screenshot, setScreenshot] = useState<string | null>(null)
  const [idleOn, setIdleOn] = useState(true)
  const [bgImage, setBgImage] = useState<string>('')
  const latestScreenshotRef = useRef<string | null>(null)
  const rafIdRef = useRef<number | null>(null)

  // 订阅宠物窗口可见性变化
  useEffect(() => {
    if (!isElectron) return

    const cleanup = petApi.onVisibilityChange((visible: boolean) => {
      setPetWindowVisible(visible)
      if (visible) {
        setPetActive(true)
      }
    })

    return () => cleanup()
  }, [isElectron, petApi])

  // 查询初始可见性状态（Bug #1 修复：消除挂载时的状态盲区）
  useEffect(() => {
    petApi.isVisible().then(result => {
      if (result.success) {
        setPetWindowVisible(result.visible)
      }
    })
  }, [])

  // 订阅截图更新（requestAnimationFrame 节流）
  useEffect(() => {
    if (!isElectron) return

    const cleanup = petApi.onScreenshotUpdate((data: string) => {
      latestScreenshotRef.current = data
      // 用 rAF 合并多次截图更新，避免 React 频繁重渲染
      if (rafIdRef.current === null) {
        rafIdRef.current = requestAnimationFrame(() => {
          rafIdRef.current = null
          setScreenshot(latestScreenshotRef.current)
        })
      }
    })

    return () => {
      cleanup()
      if (rafIdRef.current !== null) {
        cancelAnimationFrame(rafIdRef.current)
        rafIdRef.current = null
      }
    }
  }, [isElectron, petApi])

  // 加载品牌背景图（从 setting 表）
  useEffect(() => {
    apiClient
      .get('/configs/branding.background_image')
      .then((res) => {
        const data = extractData(res) as { keyValue?: string }
        if (data?.keyValue) {
          setBgImage(`${window.location.origin}/${data.keyValue}`)
        }
      })
      .catch(() => {})
  }, [])

  // 加载模型信息
  useEffect(() => {
    void (async () => {
      try {
        const [settings, directPath] = await Promise.all([
          loadPetSettings(),
          loadPetModelPath(),
        ])
        const path =
          (settings?.modelPath as string) ?? directPath ?? null
        setModelPath(path)
        setModelName(getModelName(path))
      } catch {
        setModelName('-')
      }
    })()
  }, [])

  // 订阅模型切换通知（设置页面切了模型后刷新当前信息）
  useEffect(() => {
    if (!isElectron) return

    const cleanup = petApi.onModelChanged(() => {
      void (async () => {
        try {
          const [settings, directPath] = await Promise.all([
            loadPetSettings(),
            loadPetModelPath(),
          ])
          const path = (settings?.modelPath as string) ?? directPath ?? null
          setModelPath(path)
          setModelName(getModelName(path))
        } catch {
          setModelName('-')
        }
      })()
    })

    return () => cleanup()
  }, [isElectron, petApi])

  // 刷新场景（通过 IPC 直接通知宠物窗口重载）
  const handleRefresh = useCallback(async () => {
    if (!isElectron) {
      message.warning('当前环境不支持宠物窗口')
      return
    }
    message.info('正在刷新场景...')
    const result = await petApi.reload()
    if (!result.success) {
      message.error(result.message || '刷新失败，请先显示宠物窗口')
    }
  }, [isElectron, petApi])

  // 重载模型（通过 IPC 直接通知宠物窗口重载当前模型）
  const handleReloadModel = useCallback(async () => {
    if (!isElectron) {
      message.warning('当前环境不支持宠物窗口')
      return
    }
    message.info('正在重载模型...')
    const result = await petApi.reload()
    if (!result.success) {
      message.error(result.message || '重载失败，请先显示宠物窗口')
    }
  }, [isElectron, petApi])

  // 缩放（放大缩小）
  const handleZoom = useCallback(async (factor: number) => {
    if (!isElectron) {
      message.warning('当前环境不支持宠物窗口')
      return
    }
    const result = await petApi.zoom(factor)
    if (!result.success) message.error(result.message || '缩放失败，请先显示宠物窗口')
  }, [isElectron, petApi])

  // 重置缩放
  const handleResetZoom = useCallback(async () => {
    if (!isElectron) {
      message.warning('当前环境不支持宠物窗口')
      return
    }
    const result = await petApi.resetZoom()
    if (!result.success) message.error(result.message || '重置失败，请先显示宠物窗口')
  }, [isElectron, petApi])

  // 待机动画（动作）开关
  const handleToggleIdle = useCallback(async (checked: boolean) => {
    setIdleOn(checked)
    if (!isElectron) {
      message.warning('当前环境不支持宠物窗口')
      return
    }
    const result = await petApi.setIdle(checked)
    if (!result.success) message.error(result.message || '设置失败，请先显示宠物窗口')
  }, [isElectron, petApi])

  // 切换宠物显示/隐藏 - 使用 IPC 返回值，不依赖闭包状态
  const handleTogglePet = async () => {
    if (!isElectron) {
      message.warning('当前环境不支持宠物窗口')
      return
    }
    const result = await petApi.toggle()
    if (result.success) {
      message.success(result.visible ? '宠物窗口已显示' : '宠物窗口已隐藏')
      setPetWindowVisible(result.visible)
    } else {
      message.error('操作失败')
    }
  }

  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      {/* 顶部：大幅预览区 - 主要视觉焦点 */}
      <div
        style={{
          width: '100%',
          height: 300,
          borderRadius: 10,
          overflow: 'hidden',
          background: bgImage
            ? `url(${bgImage}) center/cover no-repeat`
            : 'linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)',
          border: '1px solid rgba(255,255,255,0.06)',
          transition: 'background 0.3s ease',
        }}
      >
        <PetScreenshotPreview
          screenshot={screenshot}
          petVisible={petWindowVisible}
          onClick={handleTogglePet}
        />
      </div>

      {/* 中间：操作按钮栏 */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
        <Button
          icon={petWindowVisible ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
          type="primary"
          onClick={handleTogglePet}
          size="middle"
        >
          {petWindowVisible ? '隐藏宠物' : '显示宠物'}
        </Button>
        <Button icon={<SyncOutlined />} onClick={handleRefresh}>
          刷新
        </Button>
        <Button icon={<ReloadOutlined />} onClick={handleReloadModel}>
          重载模型
        </Button>
      </div>

      {/* 交互控制：缩放 + 待机动作 */}
      <Card size="small" title="交互控制" styles={{ body: { padding: '12px 16px' } }}>
        <Space direction="vertical" size={10} style={{ width: '100%' }}>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <Text type="secondary" style={{ width: 40 }}>缩放</Text>
            <Button size="small" icon={<ZoomInOutlined />} onClick={() => handleZoom(1.15)}>放大</Button>
            <Button size="small" icon={<ZoomOutOutlined />} onClick={() => handleZoom(1 / 1.15)}>缩小</Button>
            <Button size="small" icon={<ReloadOutlined />} onClick={handleResetZoom}>重置</Button>
          </div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', justifyContent: 'space-between' }}>
            <Text type="secondary">待机动作</Text>
            <Switch checked={idleOn} onChange={handleToggleIdle} checkedChildren="开" unCheckedChildren="关" />
          </div>
        </Space>
      </Card>

      {/* 下方：状态信息横向排列 */}
      <Row gutter={12}>
        {/* 模型信息 */}
        <Col span={14}>
          <Card size="small" title="模型信息" styles={{ body: { padding: '12px 16px' } }}>
            <Space orientation="vertical" size={4} style={{ width: '100%' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <Text type="secondary">名称</Text>
                <Text>{modelName}</Text>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <Text type="secondary">版本</Text>
                <Text>{modelPath ? '已加载' : '-'}</Text>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <Text type="secondary">渲染引擎</Text>
                <Text>Three.js + MMDLoader</Text>
              </div>
            </Space>
          </Card>
        </Col>

        {/* 实时状态 */}
        <Col span={10}>
          <Card size="small" title="实时状态" styles={{ body: { padding: '12px 16px' } }}>
            <Space orientation="vertical" size={8} style={{ width: '100%' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Badge status={petActive ? 'success' : 'default'} />
                <Text>{petActive ? '宠物已启动' : '宠物未启动'}</Text>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Badge status={petWindowVisible ? 'success' : 'default'} />
                <Text>桌面窗口: {petWindowVisible ? '已显示' : '未显示'}</Text>
              </div>
            </Space>
          </Card>
        </Col>
      </Row>
    </Space>
  )
}
