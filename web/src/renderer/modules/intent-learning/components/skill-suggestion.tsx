import { Alert, Button, Space, Empty } from 'antd'
import { CheckOutlined, CloseOutlined } from '@ant-design/icons'
import { useSkillSuggestions } from '../hooks/use-intent-learning'

export default function SkillSuggestion() {
  const { data: suggestions = [], isLoading, acceptSuggestion, ignoreSuggestion } = useSkillSuggestions()

  if (isLoading) return null
  if (suggestions.length === 0) return <Empty description="暂无技能建议" />

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="middle">
      {suggestions.map((suggestion) => (
        <Alert
          key={suggestion.id}
          type="info"
          showIcon
          message={suggestion.name}
          description={
            <div>
              <p style={{ margin: '8px 0' }}>{suggestion.description}</p>
              <Space>
                <Button
                  type="primary"
                  size="small"
                  icon={<CheckOutlined />}
                  onClick={() => acceptSuggestion(suggestion.id)}
                >
                  创建技能
                </Button>
                <Button
                  size="small"
                  icon={<CloseOutlined />}
                  onClick={() => ignoreSuggestion(suggestion.id)}
                >
                  忽略
                </Button>
              </Space>
            </div>
          }
        />
      ))}
    </Space>
  )
}
