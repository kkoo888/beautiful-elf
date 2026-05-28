import { Row, Col, Space, Button, Typography, Timeline, Spin, Card } from 'antd'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import 'dayjs/locale/zh-cn'
import AttributeBar from './attribute-bar'
import { usePet } from '../hooks/use-pet'
import { PET_INTERACTION_META, type PetInteractionType } from '../types/pet'

dayjs.extend(relativeTime)
dayjs.locale('zh-cn')

const ATTR_CONFIG = [
  { key: 'hunger', label: '饥饿', icon: '🍖', color: '#f97316' },
  { key: 'clean', label: '清洁', icon: '🧹', color: '#3b82f6' },
  { key: 'mood', label: '心情', icon: '😊', color: '#22c55e' },
  { key: 'health', label: '健康', icon: '❤️', color: '#ef4444' },
  { key: 'intimacy', label: '亲密', icon: '💕', color: '#ec4899' },
  { key: 'level', label: '等级', icon: '⭐', color: '#eab308' },
] as const

export default function PetStatusTab() {
  const { attributes, isLoading, interact, interactions } = usePet()

  if (isLoading) {
    return (
      <div style={{ textAlign: 'center', padding: 40 }}>
        <Spin />
      </div>
    )
  }

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="middle">
      <Card size="small" title="宠物属性">
        <Row gutter={[16, 8]}>
          {ATTR_CONFIG.map(({ key, label, icon, color }) => (
            <Col span={12} key={key}>
              <AttributeBar label={label} value={attributes[key]} icon={icon} color={color} />
            </Col>
          ))}
        </Row>
      </Card>

      <Card size="small" title="互动操作">
        <Space wrap>
          {(Object.keys(PET_INTERACTION_META) as PetInteractionType[]).map((type) => {
            const meta = PET_INTERACTION_META[type]
            return (
              <Button
                key={type}
                icon={<span>{meta.icon}</span>}
                style={{ borderColor: meta.color, color: meta.color }}
                onClick={() => interact(type)}
              >
                {meta.label}
              </Button>
            )
          })}
        </Space>
      </Card>

      <Card size="small" title="互动记录">
        <Timeline
          items={interactions.map((item) => ({
            children: (
              <span>
                <Typography.Text strong>
                  {PET_INTERACTION_META[item.type].icon} {PET_INTERACTION_META[item.type].label}
                </Typography.Text>
                <br />
                <Typography.Text type="secondary">{item.effect}</Typography.Text>
                <br />
                <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                  {dayjs(item.createdAt).fromNow()}
                </Typography.Text>
              </span>
            ),
            color: PET_INTERACTION_META[item.type].color,
          }))}
        />
      </Card>
    </Space>
  )
}
