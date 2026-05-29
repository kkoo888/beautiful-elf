import { Row, Col, Space, Button, Card, Switch, Typography, Badge, Tag, Select } from 'antd'
import {
  CloseCircleOutlined,
  ReloadOutlined,
  SyncOutlined,
  PlayCircleOutlined,
  SmileOutlined,
  ThunderboltOutlined,
  SettingOutlined,
} from '@ant-design/icons'
import { usePet } from '../hooks/use-pet'
import { FPS_OPTIONS } from '../types/pet'
import PetPreview from './pet-preview'

const { Text } = Typography

/** 状态指示器 */
function StatusDot({ active, label }: { active: boolean; label: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <Badge status={active ? 'success' : 'default'} />
      <Text type={active ? undefined : 'secondary'}>{label}</Text>
    </div>
  )
}

/** 信息行 */
function InfoRow({ label, value }: { label: string; value: string | number }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0' }}>
      <Text type="secondary">{label}</Text>
      <Text>{value}</Text>
    </div>
  )
}

export default function PetControlTab() {
  const {
    windowVisible,
    screenshot,
    toggleWindow,
    modelInfo,
    runtimeStatus,
    refreshModelInfo,
    toggleMouseFollow,
    setFps,
    playExpression,
    playMotion,
  } = usePet()

  return (
    <Row gutter={16} style={{ width: '100%' }}>
      {/* 左侧：预览区 */}
      <Col span={14}>
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          {/* 操作按钮栏 */}
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <Button
              icon={windowVisible ? <CloseCircleOutlined /> : <PlayCircleOutlined />}
              type={windowVisible ? 'default' : 'primary'}
              danger={windowVisible}
              onClick={toggleWindow}
            >
              {windowVisible ? '关闭宠物窗口' : '打开宠物窗口'}
            </Button>
            <Button icon={<SyncOutlined />} onClick={refreshModelInfo} disabled={!windowVisible}>
              刷新
            </Button>
            <Button icon={<ReloadOutlined />} disabled={!windowVisible}>
              重载模型
            </Button>
            <Button icon={<SmileOutlined />} disabled={!windowVisible} onClick={() => playExpression()}>
              播放表情
            </Button>
            <Button icon={<ThunderboltOutlined />} disabled={!windowVisible} onClick={() => playMotion()}>
              播放动作
            </Button>
          </div>

          {/* 预览窗口 */}
          <PetPreview screenshot={screenshot} visible={windowVisible} onToggle={toggleWindow} />

          {/* 模型就绪状态 */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '8px 12px',
              background: 'var(--ant-color-fill-quaternary)',
              borderRadius: 8,
            }}
          >
            <div>
              <Text strong>{modelInfo.name || '无模型'}</Text>
              <Text type="secondary" style={{ marginLeft: 8 }}>
                · {modelInfo.engine}
              </Text>
            </div>
            <Tag color={modelInfo.ready ? 'success' : 'default'}>
              {modelInfo.ready ? '模型就绪' : '未启动'}
            </Tag>
          </div>
        </Space>
      </Col>

      {/* 右侧：功能与状态 */}
      <Col span={10}>
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          {/* 鼠标跟随 */}
          <Card
            size="small"
            title={
              <span>
                <SettingOutlined style={{ marginRight: 8 }} />
                鼠标跟随
              </span>
            }
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <Text type="secondary" style={{ fontSize: 12 }}>
                开启后模型眼睛将跟随鼠标移动
              </Text>
              <Switch
                checked={runtimeStatus.mouseFollow}
                onChange={toggleMouseFollow}
                disabled={!windowVisible}
              />
            </div>
          </Card>

          {/* 模型信息 */}
          <Card
            size="small"
            title={
              <span>
                <SettingOutlined style={{ marginRight: 8 }} />
                模型信息
              </span>
            }
          >
            <InfoRow label="名称" value={modelInfo.name || '-'} />
            <InfoRow label="版本" value={modelInfo.version || '-'} />
            <InfoRow label="表情数" value={modelInfo.expressionCount} />
            <InfoRow label="动作数" value={modelInfo.motionCount} />
            <InfoRow label="鼠标跟随" value={runtimeStatus.mouseFollow ? '开启' : '关闭'} />
          </Card>

          {/* 宠物实时状态 */}
          <Card
            size="small"
            title={
              <span>
                <span style={{ marginRight: 8 }}>🐾</span>
                宠物实时状态
              </span>
            }
          >
            <Space direction="vertical" size={4} style={{ width: '100%' }}>
              <StatusDot active={runtimeStatus.libraryLoaded} label={`库加载: ${runtimeStatus.libraryLoaded ? '已加载' : '等待中'}`} />
              <StatusDot active={runtimeStatus.mouseFollow} label={`鼠标跟随: ${runtimeStatus.mouseFollow ? '开启' : '关闭'}`} />
              <StatusDot active={runtimeStatus.clickInteraction} label={`点击交互: ${runtimeStatus.clickInteraction ? '开启' : '关闭'}`} />
              <InfoRow label="当前表情" value={runtimeStatus.currentExpression} />
              <InfoRow label="当前动作" value={runtimeStatus.currentMotion} />
              <StatusDot active={runtimeStatus.lipSync} label={`嘴型同步: ${runtimeStatus.lipSync ? '开启' : '关闭'}`} />
              <InfoRow label="对话气泡" value={runtimeStatus.bubbleText || '无'} />
              <InfoRow label="动作队列" value={runtimeStatus.motionQueueCount > 0 ? `播放中 (${runtimeStatus.motionQueueCount})` : '空闲'} />

              {/* 帧率选择 */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 8 }}>
                <Text type="secondary">帧率</Text>
                <Select
                  size="small"
                  style={{ width: 120 }}
                  value={runtimeStatus.fps}
                  onChange={setFps}
                  options={FPS_OPTIONS.map((o) => ({ label: o.label, value: o.value }))}
                  disabled={!windowVisible}
                />
              </div>
            </Space>
          </Card>
        </Space>
      </Col>
    </Row>
  )
}
