/** 技能 API 服务（mock 实现，后续替换为真实 API） */

import { apiClient } from '@/services/api-client'
import type { Skill, InstallSkillInput, RefineResult } from '../types/skills'

// ─── Mock 数据 ────────────────────────────────────────────

function delay(ms = 300): Promise<void> {
  return new Promise((r) => setTimeout(r, ms))
}

function generateId(): string {
  return `skill_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
}

const now = new Date().toISOString()

const mockSkills: Skill[] = [
  {
    id: 'skill_001',
    name: 'weather',
    description: '获取当前天气和预报，支持全球城市查询',
    version: '1.2.0',
    enabled: true,
    triggerWords: ['天气', '气温', 'weather', 'forecast'],
    dependencies: [],
    stats: { callCount: 128, successRate: 0.97, avgDuration: 850 },
    createdAt: now,
  },
  {
    id: 'skill_002',
    name: 'github',
    description: '使用 gh CLI 与 GitHub 交互，管理 issue、PR、CI',
    version: '2.0.1',
    enabled: true,
    triggerWords: ['github', 'issue', 'pr', 'pull request'],
    dependencies: ['gh'],
    stats: { callCount: 64, successRate: 0.92, avgDuration: 1200 },
    createdAt: now,
  },
  {
    id: 'skill_003',
    name: 'summarize',
    description: '使用 summarize CLI 总结网页、PDF、图片、音频、YouTube',
    version: '1.0.3',
    enabled: false,
    triggerWords: ['总结', '摘要', 'summarize', 'summary'],
    dependencies: [],
    stats: { callCount: 45, successRate: 0.89, avgDuration: 2100 },
    createdAt: now,
  },
  {
    id: 'skill_004',
    name: 'chart-image',
    description: '生成高质量图表图片，支持折线、柱状、饼图等多种类型',
    version: '1.1.0',
    enabled: true,
    triggerWords: ['图表', 'chart', 'graph', 'plot'],
    dependencies: [],
    stats: { callCount: 31, successRate: 0.95, avgDuration: 1500 },
    createdAt: now,
  },
  {
    id: 'skill_005',
    name: 'excel-xlsx',
    description: '创建和编辑 Excel 工作簿，支持公式、格式、模板',
    version: '1.0.0',
    enabled: true,
    triggerWords: ['excel', 'xlsx', '表格', 'spreadsheet'],
    dependencies: [],
    stats: { callCount: 19, successRate: 1.0, avgDuration: 900 },
    createdAt: now,
  },
  {
    id: 'skill_006',
    name: 'tts-wav',
    description: '使用 MiMo TTS 生成语音或歌曲 WAV 文件',
    version: '0.9.0',
    enabled: false,
    triggerWords: ['朗读', '语音', 'tts', 'speak', 'sing'],
    dependencies: [],
    stats: { callCount: 8, successRate: 0.75, avgDuration: 3200 },
    createdAt: now,
  },
]

let mockStore = [...mockSkills]

// ─── API 函数 ─────────────────────────────────────────────

/** 获取技能列表 */
export async function fetchSkills(): Promise<Skill[]> {
  await delay()
  try {
    const { data } = await apiClient.get('/skills')
    return (data as { data: Skill[] }).data
  } catch {
    return [...mockStore]
  }
}

/** 安装技能 */
export async function installSkill(input: InstallSkillInput): Promise<Skill> {
  await delay(800)
  try {
    const { data } = await apiClient.post('/skills/install', input)
    return (data as { data: Skill }).data
  } catch {
    const skill: Skill = {
      id: generateId(),
      name: input.source === 'github' ? input.content.split('/').pop() ?? 'unknown' : 'imported-skill',
      description: '从 ' + (input.source === 'file' ? '文件' : 'GitHub') + ' 导入的技能',
      version: '0.1.0',
      enabled: true,
      triggerWords: [],
      dependencies: [],
      stats: { callCount: 0, successRate: 1, avgDuration: 0 },
      createdAt: new Date().toISOString(),
    }
    mockStore = [...mockStore, skill]
    return skill
  }
}

/** 切换技能启用/禁用 */
export async function toggleSkill(id: string, enabled: boolean): Promise<Skill> {
  await delay(200)
  try {
    const { data } = await apiClient.put(`/skills/${id}/toggle`, { enabled })
    return (data as { data: Skill }).data
  } catch {
    const idx = mockStore.findIndex((s) => s.id === id)
    if (idx === -1) throw new Error('Skill not found')
    mockStore[idx] = { ...mockStore[idx], enabled }
    return mockStore[idx]
  }
}

/** 获取技能使用统计 */
export async function fetchSkillStats(id: string): Promise<Skill['stats']> {
  await delay()
  try {
    const { data } = await apiClient.get(`/skills/${id}/stats`)
    return (data as { data: Skill['stats'] }).data
  } catch {
    const skill = mockStore.find((s) => s.id === id)
    return skill?.stats ?? { callCount: 0, successRate: 0, avgDuration: 0 }
  }
}

/** 炼化技能（LLM 优化建议） */
export async function refineSkill(id: string, prompt?: string): Promise<RefineResult> {
  await delay(1500)
  try {
    const { data } = await apiClient.post(`/skills/${id}/refine`, { prompt })
    return (data as { data: RefineResult }).data
  } catch {
    const skill = mockStore.find((s) => s.id === id)
    const name = skill?.name ?? 'unknown'
    return {
      suggestions: [
        `为 ${name} 添加更多触发词以提高匹配率`,
        `优化 ${name} 的错误处理逻辑`,
        `添加使用示例到 SKILL.md 中`,
      ],
      refinedContent: `# ${name} (Refined)\n\n> 经过 AI 优化的技能描述\n\n${skill?.description ?? ''}\n\n## 优化建议\n\n- 增强触发词覆盖\n- 改进错误消息\n- 添加边界条件处理`,
    }
  }
}
