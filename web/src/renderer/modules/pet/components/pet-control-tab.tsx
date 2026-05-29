import { Card, Button, Space, Badge, Row, Col } from 'antd'
import {
  CloseOutlined,
  ReloadOutlined,
  SyncOutlined,
  PlayCircleOutlined,
} from '@ant-design/icons'
import { useElectronApi } from '@/hooks'
import PetScreenshotPreview from './pet-screenshot-preview'

export default function PetControlTab() {
  const { pet: petApi, isElectron } = useElectronApi()

  const handleTogglePet = async () => {
    if (isElectron) {
      await petApi.toggle()
    }
  }

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
        <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
          {/* 操作 */}
          <Card size="small" title="操作">
            <Space wrap>
              <Button
                icon={<PlayCircleOutlined />}
                type="primary"
                onClick={handleTogglePet}
              >
                显示宠物
              </Button>
              <Button icon={<SyncOutlined />}>刷新</Button>
              <Button icon={<ReloadOutlined />} type="primary">
                重载模型
              </Button>
            </Space>
          </Card>

          {/* 模型信息 */}
          <Card size="small" title="模型信息">
            <div style={{ fontSize: 13, color: 'var(--ant-color-text-secondary)' }}>
              切换模型后请重载
            </div>
          </Card>

          {/* 实时状态 */}
          <Card size="small" title="实时状态">
            <Space orientation="vertical" size="small" style={{ width: '100%' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Badge status="default" />
                <span>宠物未启动</span>
              </div>
            </Space>
          </Card>
        </Space>
      </Col>
    </Row>
  )
}
