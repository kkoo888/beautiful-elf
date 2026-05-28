import dayjs from 'dayjs'
import type { IntentCorrection, BehaviorPattern, SkillSuggestion } from '../types/intent-learning'

const MOCK_CORRECTIONS: IntentCorrection[] = [
  { id: '1', originalIntent: '帮我写个周报', correctModule: '工作流', createdAt: dayjs().subtract(1, 'hour').toISOString() },
  { id: '2', originalIntent: '翻译这段话', correctModule: '翻译', createdAt: dayjs().subtract(2, 'hour').toISOString() },
  { id: '3', originalIntent: '记住我的密码是...', correctModule: '记忆', createdAt: dayjs().subtract(3, 'hour').toISOString() },
  { id: '4', originalIntent: '帮我剪贴这段代码', correctModule: '剪贴板', createdAt: dayjs().subtract(5, 'hour').toISOString() },
  { id: '5', originalIntent: '明天下午三点开会', correctModule: '日程', createdAt: dayjs().subtract(8, 'hour').toISOString() },
  { id: '6', originalIntent: '这段代码有bug', correctModule: '代码片段', createdAt: dayjs().subtract(12, 'hour').toISOString() },
  { id: '7', originalIntent: '关于Rust的知识', correctModule: '知识库', createdAt: dayjs().subtract(1, 'day').toISOString() },
]

const MOCK_PATTERNS: BehaviorPattern[] = [
  { id: '1', description: '每天早上查看日程并整理待办', frequency: 28, actions: ['查询日程', '列出待办', '设置提醒'] },
  { id: '2', description: '翻译收到的外文消息后回复', frequency: 15, actions: ['接收消息', '检测语言', '翻译', '回复'] },
  { id: '3', description: '复制代码片段到剪贴板后格式化', frequency: 22, actions: ['复制代码', '检测语言', '格式化', '保存'] },
  { id: '4', description: '写周报时先汇总本周工作', frequency: 8, actions: ['查询工作记录', '分类汇总', '生成周报', '导出'] },
]

const MOCK_SUGGESTIONS: SkillSuggestion[] = [
  { id: '1', patternId: '1', name: '早间日程助手', description: '自动查询当日日程并生成待办清单，支持设置提醒', createdAt: dayjs().subtract(2, 'day').toISOString() },
  { id: '2', patternId: '2', name: '智能翻译回复', description: '检测外文消息并自动翻译，生成回复建议', createdAt: dayjs().subtract(3, 'day').toISOString() },
  { id: '3', patternId: '4', name: '周报生成器', description: '基于本周工作记录自动生成周报草稿', createdAt: dayjs().subtract(5, 'day').toISOString() },
]

export async function fetchCorrections(): Promise<IntentCorrection[]> {
  try {
    // const res = await apiClient.get('/intent-learning/corrections')
    // return res.data
    throw new Error('use mock')
  } catch {
    return [...MOCK_CORRECTIONS]
  }
}

export async function fetchPatterns(): Promise<BehaviorPattern[]> {
  try {
    // const res = await apiClient.get('/intent-learning/patterns')
    // return res.data
    throw new Error('use mock')
  } catch {
    return [...MOCK_PATTERNS]
  }
}

export async function fetchSuggestions(): Promise<SkillSuggestion[]> {
  try {
    // const res = await apiClient.get('/intent-learning/suggestions')
    // return res.data
    throw new Error('use mock')
  } catch {
    return [...MOCK_SUGGESTIONS]
  }
}

export async function acceptSuggestion(id: string): Promise<void> {
  try {
    // await apiClient.post(`/intent-learning/suggestions/${id}/accept`)
    throw new Error('use mock')
  } catch {
    console.log(`Suggestion ${id} accepted (mock)`)
  }
}

export async function ignoreSuggestion(id: string): Promise<void> {
  try {
    // await apiClient.post(`/intent-learning/suggestions/${id}/ignore`)
    throw new Error('use mock')
  } catch {
    console.log(`Suggestion ${id} ignored (mock)`)
  }
}
