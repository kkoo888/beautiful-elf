/**
 * 上下文引用来源展示 — 显示 Agent 参考了哪些记忆/知识/意图
 */
import { Tag, Space, Typography, Tooltip } from 'antd'
import { DatabaseOutlined, BulbOutlined, BookOutlined, ToolOutlined } from '@ant-design/icons'
import type { ContextSource } from '../../types/chat'

const { Text } = Typography

interface ContextSourcesProps {
  /** 引用来源列表 */
  sources: ContextSource[]
}

/** 来源类型图标和颜色 */
const SOURCE_CONFIG: Record<string, { icon: React.ReactNode; color: string; label: string }> = {
  memory: { icon: <DatabaseOutlined />, color: 'purple', label: '记忆' },
  knowledge: { icon: <BookOutlined />, color: 'blue', label: '知识库' },
  intent: { icon: <BulbOutlined />, color: 'cyan', label: '意图' },
  tool: { icon: <ToolOutlined />, color: 'green', label: '工具' },
}

export function ContextSourcesDisplay({ sources }: ContextSourcesProps) {
  if (!sources || sources.length === 0) return null

  return (
    <div style={{
      display: 'flex',
      flexWrap: 'wrap',
      gap: 6,
      padding: '4px 12px 8px',
    }}>
      <Text type="secondary" style={{ fontSize: 11, lineHeight: '22px' }}>
        📎 参考来源：
      </Text>
      {sources.map((source, index) => {
        const config = SOURCE_CONFIG[source.type] ?? { icon: null, color: 'default', label: source.type }
        return (
          <Tooltip
            key={`${source.type}-${index}`}
            title={source.preview || source.name}
          >
            <Tag
              icon={config.icon}
              color={config.color}
              style={{ margin: 0, fontSize: 11, cursor: 'help' }}
            >
              {source.name}
              {source.score != null && (
                <Text type="secondary" style={{ fontSize: 10, marginLeft: 4 }}>
                  {(source.score * 100).toFixed(0)}%
                </Text>
              )}
            </Tag>
          </Tooltip>
        )
      })}
    </div>
  )
}
