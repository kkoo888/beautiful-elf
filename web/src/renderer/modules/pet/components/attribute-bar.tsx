import { Progress, Typography } from 'antd'
import { WarningOutlined } from '@ant-design/icons'

interface AttributeBarProps {
  label: string
  value: number
  max?: number
  icon: string
  color: string
  /** 自定义百分比（0-100），优先于 value/max 计算 */
  percentOverride?: number
}

export default function AttributeBar({
  label,
  value,
  max = 100,
  icon,
  color,
  percentOverride,
}: AttributeBarProps) {
  const percent = percentOverride ?? Math.min(100, Math.round((value / max) * 100))
  const isLow = max <= 100 && value < 30 // 只有 0-100 范围的属性才显示低值警告

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
            {value}/{max}
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
