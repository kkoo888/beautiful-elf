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

export function SnippetsPanel() {
  return (
    <div>
      <Title level={4}>{icons['snippets'] || '📦'} Snippets</Title>
      <p>Snippets模块 - 开发中...</p>
    </div>
  )
}
