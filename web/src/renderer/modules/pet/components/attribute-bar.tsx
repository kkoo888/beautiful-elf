import { Progress, Typography } from 'antd'
import { WarningOutlined } from '@ant-design/icons'

interface AttributeBarProps {
  label: string
  value: number
  max?: number
  icon: string
  color: string
}

export default function AttributeBar({ label, value, max = 100, icon, color }: AttributeBarProps) {
  const effectiveMax = Math.max(max, value) // 防止溢出
  const percent = Math.min(100, Math.round((value / effectiveMax) * 100))
  const isLow = value < 30

  return (
    <div style={{ marginBottom: 12 }}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 4,
        }}
      >
        <Typography.Text>
          {icon} {label}
        </Typography.Text>
        <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          {isLow && <WarningOutlined style={{ color: '#ef4444' }} />}
          <Typography.Text type={isLow ? 'danger' : undefined} strong>
            {value}{value <= max ? `/${max}` : ''}
          </Typography.Text>
        </span>
      </div>
      <Progress
        percent={percent}
        strokeColor={isLow ? '#ef4444' : color}
        showInfo={false}
        size="small"
      />
    </div>
  )
}
