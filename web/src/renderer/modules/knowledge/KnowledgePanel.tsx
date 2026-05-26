import { Typography } from 'antd'

const { Title } = Typography

const icons: Record<string, string> = {
  schedule: '📅',
  clipboard: '📋',
  snippets: '💻',
  knowledge: '📚',
  memory: '🧠',
  translate: '🌐',
  skills: '🔧',
  workflow: '⚙️',
  subagent: '🤖',
  tools: '🔌',
  pet: '🐾',
  performance: '📊',
  notification: '🔔',
  settings: '⚙️'
}

export function KnowledgePanel() {
  return (
    <div>
      <Title level={4}>{icons['knowledge'] || '📦'} Knowledge</Title>
      <p>Knowledge模块 - 开发中...</p>
    </div>
  )
}
