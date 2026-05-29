import { Card, Descriptions, Button, Space, Badge, Row, Col } from 'antd'
import { ReloadOutlined, CloseOutlined, SyncOutlined } from '@ant-design/icons'
import PetScreenshotPreview from './pet-screenshot-preview'

export default function PetControlTab() {
  return (
    <Row gutter={16} style={{ width: '100%' }}>
      {/* 左侧：预览窗口 */}
      <Col span={14}>
        <Card size="small" title="预览窗口" style={{ height: '100%' }}>
          <PetScreenshotPreview />
        </Card>
      </Col>

      {/* 右侧：操作 - 模型信息 - 实时状态 */}
      <Col span={10}>
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          {/* 操作 */}
          <Card size="small" title="操作">
            <Space wrap>
              <Button icon={<CloseOutlined />} danger>
                关闭窗口
              </Button>
              <Button icon={<SyncOutlined />}>刷新</Button>
              <Button icon={<ReloadOutlined />} type="primary">
                重载模型
              </Button>
            </Space>
          </Card>

          {/* 模型信息 */}
          <Card size="small" title="模型信息">
            <Descriptions column={1} size="small">
              <Descriptions.Item label="模型名称">Beautiful-Elf Pet v3.2</Descriptions.Item>
              <Descriptions.Item label="模型版本">3.2.1</Descriptions.Item>
              <Descriptions.Item label="渲染引擎">Canvas 2D</Descriptions.Item>
              <Descriptions.Item label="动画帧率">60 FPS</Descriptions.Item>
            </Descriptions>
          </Card>

          {/* 实时状态 */}
          <Card size="small" title="实时状态">
            <Space direction="vertical" size="small" style={{ width: '100%' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Badge status="success" />
                <span>宠物运行中</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Badge status="success" />
                <span>桌面窗口: 已显示</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Badge status="processing" />
                <span>动画: 空闲状态</span>
              </div>
            </Space>
          </Card>
        </Space>
      </Col>
    </Row>
  )
}
