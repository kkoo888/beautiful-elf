import { Button, Space, Badge, Row, Col, Card, Typography } from 'antd'
import {
  CloseOutlined,
  ReloadOutlined,
  SyncOutlined,
  PlayCircleOutlined,
} from '@ant-design/icons'
import { useElectronApi } from '@/hooks'
import PetScreenshotPreview from './pet-screenshot-preview'

const { Text } = Typography

export default function PetControlTab() {
  const { pet: petApi, isElectron } = useElectronApi()

  const handleTogglePet = async () => {
    if (isElectron) {
      await petApi.toggle()
    }
  }

  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      {/* 顶部：操作按钮栏 */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <Button icon={<PlayCircleOutlined />} type="primary" onClick={handleTogglePet}>
          显示宠物
        </Button>
        <Button icon={<SyncOutlined />}>刷新</Button>
        <Button icon={<ReloadOutlined />}>重载模型</Button>
      </div>

      {/* 下方：左侧预览 + 右侧状态 */}
      <Row gutter={16}>
        {/* 左侧：预览区 */}
        <Col span={14}>
          <div
            style={{
              width: '100%',
              height: 300,
              borderRadius: 8,
              overflow: 'hidden',
              background: '#1a1a2e',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <PetScreenshotPreview />
          </div>
        </Col>

        {/* 右侧：卡片堆叠 */}
        <Col span={10}>
          <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
            {/* 模型信息 */}
            <Card size="small" title="模型信息">
              <Space orientation="vertical" size={4} style={{ width: '100%' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Text type="secondary">名称</Text>
                  <Text>-</Text>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Text type="secondary">版本</Text>
                  <Text>-</Text>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Text type="secondary">渲染引擎</Text>
                  <Text>-</Text>
                </div>
              </Space>
            </Card>

            {/* 实时状态 */}
            <Card size="small" title="实时状态">
              <Space orientation="vertical" size={4} style={{ width: '100%' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Badge status="default" />
                  <Text>宠物未启动</Text>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Badge status="default" />
                  <Text>桌面窗口: 未显示</Text>
                </div>
              </Space>
            </Card>
          </Space>
        </Col>
      </Row>
    </Space>
  )
}
