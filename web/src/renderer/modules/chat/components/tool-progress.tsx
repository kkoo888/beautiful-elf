/**
 * 工具执行进度指示器 — 展示 Agent 正在调用哪些工具
 */
import { Tag, Spin, Space, Typography, Collapse } from 'antd'
import { CheckCircleOutlined, LoadingOutlined, ToolOutlined } from '@ant-design/icons'
import type { ToolProgress } from '../../types/chat'

const { Text } = Typography

interface ToolProgressIndicatorProps {
  /** 工具进度列表 */
  tools: ToolProgress[]
}

/** 工具中文名映射（常见工具） */
const TOOL_LABELS: Record<string, string> = {
  search_knowledge: '📚 搜索知识库',
  search_memory: '🧠 搜索记忆',
  web_search: '🌐 网络搜索',
  execute_code: '💻 执行代码',
  read_file: '📄 读取文件',
  write_file: '✏️ 写入文件',
  api_call: '🔗 API 调用',
  database_query: '🗄️ 数据库查询',
}

export function ToolProgressIndicator({ tools }: ToolProgressIndicatorProps) {
  if (!tools || tools.length === 0) return null

  return (
    <div style={{
      padding: '8px 12px',
      margin: '8px 0',
      background: '#fafafa',
      borderRadius: 8,
      border: '1px solid #f0f0f0',
    }}>
      <Space direction="vertical" size={4} style={{ width: '100%' }}>
        {tools.map((tool, index) => {
          const label = TOOL_LABELS[tool.tool] ?? tool.tool
          const isRunning = tool.status === 'running'
          const duration = tool.startTime ? Date.now() - tool.startTime : 0

          return (
            <div key={`${tool.tool}-${index}`} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              {isRunning ? (
                <Spin indicator={<LoadingOutlined style={{ fontSize: 14 }} />} size="small" />
              ) : (
                <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 14 }} />
              )}
              <Text style={{ fontSize: 13, flex: 1 }}>
                {label}
              </Text>
              {isRunning ? (
                <Tag color="processing">执行中…</Tag>
              ) : (
                <Tag color="success">完成 {duration > 0 ? `${(duration / 1000).toFixed(1)}s` : ''}</Tag>
              )}
            </div>
          )
        })}
      </Space>

      {/* 已完成工具的输出预览（可折叠） */}
      {tools.some((t) => t.status === 'done' && t.outputPreview) && (
        <Collapse
          size="small"
          ghost
          items={tools
            .filter((t) => t.status === 'done' && t.outputPreview)
            .map((t) => ({
              key: t.tool,
              label: <Text style={{ fontSize: 12 }}>{TOOL_LABELS[t.tool] ?? t.tool} 输出</Text>,
              children: (
                <pre style={{
                  margin: 0,
                  padding: '6px 10px',
                  background: '#f6f8fa',
                  borderRadius: 6,
                  fontSize: 11,
                  maxHeight: 150,
                  overflow: 'auto',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-all',
                }}>
                  {t.outputPreview}
                </pre>
              ),
            }))}
          style={{ marginTop: 4 }}
        />
      )}
    </div>
  )
}
