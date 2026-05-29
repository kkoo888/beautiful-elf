import { Card, Tag, Typography, Space, Empty } from 'antd'
import { useBehaviorPatterns } from '../hooks/use-intent-learning'

export default function PatternDisplay() {
  const { data: patterns = [], isLoading } = useBehaviorPatterns()

  if (isLoading) return null
  if (patterns.length === 0) return <Empty description="暂无行为模式" />

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="middle">
      {patterns.map((pattern) => (
        <Card key={pattern.id} size="small">
          <Typography.Paragraph style={{ marginBottom: 8 }}>
            {pattern.description}
          </Typography.Paragraph>
          <div style={{ marginBottom: 8 }}>
            <Typography.Text type="secondary">触发频率：{pattern.frequency} 次</Typography.Text>
          </div>
          <Space wrap size={[4, 4]}>
            {pattern.actions.map((action, index) => (
              <Tag key={index} color="geekblue">
                {index + 1}. {action}
              </Tag>
            ))}
          </Space>
        </Card>
      ))}
    </Space>
  )
}
