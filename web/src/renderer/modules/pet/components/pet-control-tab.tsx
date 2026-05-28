import { Card, Switch, Descriptions, Button, Space, Tag, Badge } from 'antd'
import { ReloadOutlined, CloseOutlined, SyncOutlined } from '@ant-design/icons'
import { useState } from 'react'

export default function PetControlTab() {
  const [desktopPetEnabled, setDesktopPetEnabled] = useState(true)

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="middle">
      <Card size="small" title="桌面宠物">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span>启用桌面宠物</span>
          <Switch checked={desktopPetEnabled} onChange={setDesktopPetEnabled} />
        </div>
      </Card>

      <Card size="small" title="模型信息">
        <Descriptions column={1} size="small">
          <Descriptions.Item label="模型名称">Beautiful-Elf Pet v3.2</Descriptions.Item>
          <Descriptions.Item label="模型版本">3.2.1</Descriptions.Item>
          <Descriptions.Item label="渲染引擎">Canvas 2D</Descriptions.Item>
          <Descriptions.Item label="动画帧率">60 FPS</Descriptions.Item>
        </Descriptions>
      </Card>

      <Card size="small" title="实时状态">
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Badge status="success" />
            <span>宠物运行中</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Badge status={desktopPetEnabled ? 'success' : 'default'} />
            <span>桌面窗口: {desktopPetEnabled ? '已显示' : '已隐藏'}</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Badge status="processing" />
            <span>动画: 空闲状态</span>
          </div>
        </Space>
      </Card>

      <Card size="small" title="操作">
        <Space wrap>
          <Button icon={<CloseOutlined />} danger>
            关闭窗口
          </Button>
          <Button icon={<SyncOutlined />}>
            刷新
          </Button>
          <Button icon={<ReloadOutlined />} type="primary">
            重载模型
          </Button>
        </Space>
      </Card>
    </Space>
  )
}
