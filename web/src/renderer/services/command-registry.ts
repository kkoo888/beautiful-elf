import type { Command } from '@/types'

/**
 * 命令注册表
 * 支持模块动态注册命令，内置导航命令
 */

/** 创建导航命令 */
export function createNavigationCommand(
  id: string,
  name: string,
  icon: string,
  keywords: string[],
  navigate: (path: string) => void
): Command {
  return {
    id,
    name,
    icon,
    keywords,
    module: getModuleGroup(id),
    action: () => navigate(id === 'chat' ? '/' : `/${id}`),
    use_count: 0
  }
}

/** 根据模块 ID 获取分组名 */
function getModuleGroup(id: string): string {
  const groups: Record<string, string> = {
    chat: 'core',
    schedule: 'core',
    clipboard: 'core',
    snippets: 'core',
    knowledge: 'knowledge',
    memory: 'knowledge',
    translate: 'knowledge',
    skills: 'knowledge',
    workflow: 'automation',
    subagent: 'automation',
    tools: 'automation',
    pet: 'system',
    performance: 'system',
    notification: 'system',
    settings: 'system'
  }
  return groups[id] || 'other'
}

/** 内置导航命令定义 */
export const BUILTIN_NAV_ITEMS = [
  { id: 'chat', name: '对话', icon: '💬', keywords: ['chat', '对话', '聊天'] },
  { id: 'schedule', name: '日程', icon: '📅', keywords: ['schedule', '日程', '日历'] },
  { id: 'clipboard', name: '剪贴板', icon: '📋', keywords: ['clipboard', '剪贴板', '复制'] },
  { id: 'snippets', name: '代码片段', icon: '💻', keywords: ['snippets', '代码', '片段'] },
  { id: 'knowledge', name: '知识库', icon: '📚', keywords: ['knowledge', '知识', '文档'] },
  { id: 'memory', name: '记忆', icon: '🧠', keywords: ['memory', '记忆', '长期记忆'] },
  { id: 'translate', name: '翻译', icon: '🌐', keywords: ['translate', '翻译'] },
  { id: 'skills', name: '技能', icon: '🔧', keywords: ['skills', '技能', '插件'] },
  { id: 'workflow', name: '工作流', icon: '⚙️', keywords: ['workflow', '工作流', '流程'] },
  { id: 'subagent', name: '子代理', icon: '🤖', keywords: ['subagent', '子代理', '代理'] },
  { id: 'tools', name: '工具管理', icon: '🔌', keywords: ['tools', '工具', '管理'] },
  { id: 'pet', name: '宠物', icon: '🐾', keywords: ['pet', '宠物', '桌面宠物'] },
  { id: 'performance', name: '性能监控', icon: '📊', keywords: ['performance', '性能', '监控'] },
  { id: 'notification', name: '通知', icon: '🔔', keywords: ['notification', '通知', '消息'] },
  { id: 'settings', name: '设置', icon: '⚙️', keywords: ['settings', '设置', '配置'] }
]
