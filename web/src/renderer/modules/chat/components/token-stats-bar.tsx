/**
 * Token 统计栏 — 显示当前对话的 token 消耗
 */
import { Space, Tag, Typography } from 'antd'
import { ThunderboltOutlined } from '@ant-design/icons'

const { Text } = Typography

interface TokenStatsBarProps {
  /** prompt token 数 */
  promptTokens: number
  /** completion token 数 */
  completionTokens: number
  /** 执行耗时 ms（可选） */
  durationMs?: number
}

export function TokenStatsBar({ promptTokens, completionTokens, durationMs }: TokenStatsBarProps) {
  if (!promptTokens && !completionTokens) return null

  const total = promptTokens + completionTokens

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'flex-end',
      padding: '4px 12px',
      gap: 12,
    }}>
      <Space size={8}>
        <Tag icon={<ThunderboltOutlined />} color="blue" style={{ margin: 0 }}>
          {total.toLocaleString()} tokens
        </Tag>
        <Text type="secondary" style={{ fontSize: 11 }}>
          输入 {promptTokens.toLocaleString()} / 输出 {completionTokens.toLocaleString()}
        </Text>
        {durationMs != null && durationMs > 0 && (
          <Text type="secondary" style={{ fontSize: 11 }}>
            · {(durationMs / 1000).toFixed(1)}s
          </Text>
        )}
      </Space>
    </div>
  )
}
