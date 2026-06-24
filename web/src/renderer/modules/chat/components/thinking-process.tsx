import { useState } from 'react'
import { Typography, Tag } from 'antd'
import {
  BulbOutlined,
  CheckCircleOutlined,
  LoadingOutlined,
  RightOutlined,
} from '@ant-design/icons'

const { Text } = Typography

interface ThinkingStep {
  id: string
  content: string
  status: 'thinking' | 'done' | 'error'
  timestamp?: number
}

interface ThinkingProcessProps {
  steps: ThinkingStep[]
  isThinking?: boolean
}

export function ThinkingProcess({ steps, isThinking = false }: ThinkingProcessProps) {
  const [expanded, setExpanded] = useState(false)

  if (steps.length === 0 && !isThinking) return null

  const getStatusIcon = (status: ThinkingStep['status']) => {
    switch (status) {
      case 'thinking':
        return <LoadingOutlined spin style={{ color: '#1677ff', fontSize: 13 }} />
      case 'done':
        return <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 13 }} />
      case 'error':
        return <CheckCircleOutlined style={{ color: '#ff4d4f', fontSize: 13 }} />
    }
  }

  return (
    <div style={{ margin: '8px 16px', border: '1px solid #f0f0f0', borderRadius: 8, background: '#fafafa', overflow: 'hidden' }}>
      <div
        style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 14px', cursor: 'pointer' }}
        onClick={() => setExpanded(!expanded)}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <BulbOutlined style={{ color: '#1677ff', fontSize: 14 }} />
          <Text style={{ fontSize: 13, fontWeight: 500, margin: 0 }}>思考过程</Text>
          <Tag color="blue" style={{ fontSize: 11, lineHeight: '18px', padding: '0 6px' }}>
            {steps.length} 步
          </Tag>
        </div>
        <RightOutlined
          style={{ fontSize: 10, color: '#999', transition: 'transform 0.2s', transform: expanded ? 'rotate(90deg)' : 'none' }}
        />
      </div>

      {expanded && (
        <div style={{ padding: '8px 14px 14px' }}>
          {steps.map((step, index) => (
            <div key={step.id} style={{ display: 'flex', gap: 12 }}>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flexShrink: 0 }}>
                <div style={{
                  width: 20, height: 20, borderRadius: '50%', background: '#e6f4ff', color: '#1677ff',
                  fontSize: 11, fontWeight: 600, display: 'flex', alignItems: 'center', justifyContent: 'center'
                }}>
                  {index + 1}
                </div>
                {index < steps.length - 1 && (
                  <div style={{ width: 1, flex: 1, minHeight: 16, background: '#f0f0f0', margin: '4px 0' }} />
                )}
              </div>
              <div style={{ flex: 1, minWidth: 0, paddingBottom: 12 }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
                  {getStatusIcon(step.status)}
                  <Text style={{ fontSize: 13, lineHeight: 1.5, margin: 0 }}>{step.content}</Text>
                </div>
              </div>
            </div>
          ))}
          {isThinking && (
            <div style={{ display: 'flex', gap: 12 }}>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flexShrink: 0 }}>
                <div style={{
                  width: 20, height: 20, borderRadius: '50%', background: '#1677ff', color: '#fff',
                  fontSize: 11, fontWeight: 600, display: 'flex', alignItems: 'center', justifyContent: 'center',
                  animation: 'pulse 2s infinite'
                }}>
                  {steps.length + 1}
                </div>
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <Text style={{ fontSize: 13, fontStyle: 'italic' }} type="secondary">
                  <LoadingOutlined spin style={{ marginRight: 6 }} />
                  思考中...
                </Text>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
