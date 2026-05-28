/** 记忆 API 服务（mock 实现，后续替换为真实 API） */

import type { MemoryEntry, MemoryListResponse, MemorySearchResult } from '../types/memory'
import { generateId } from '@/utils'

// ─── Mock 数据 ────────────────────────────────────────────

const now = Date.now()
const DAY = 86400_000
const HOUR = 3600_000

const mockMemories: MemoryEntry[] = [
  {
    id: generateId(),
    summary: '用户偏好使用 TypeScript 严格模式开发，喜欢 Ant Design 组件库',
    content:
      '在讨论项目技术栈时，用户明确表示偏好 TypeScript strict mode，喜欢使用 Ant Design 作为 UI 组件库。项目采用 React 19 + Zustand 5 + TanStack Query 5 的技术栈组合。',
    conversationId: 'conv-001',
    tags: ['技术偏好', 'TypeScript', 'Ant Design'],
    createdAt: new Date(now - 7 * DAY).toISOString(),
  },
  {
    id: generateId(),
    summary: 'Beautiful-Elf 项目目标：打造温暖亲切的 AI 桌面助手',
    content:
      'Beautiful-Elf 是一款 Electron 桌面应用，核心定位是温暖亲切的 AI 助手。包含聊天、日程、知识库、记忆等功能模块，还有一个 3D 桌面宠物养成系统。',
    conversationId: 'conv-002',
    tags: ['项目', 'Beautiful-Elf', '目标'],
    createdAt: new Date(now - 5 * DAY).toISOString(),
  },
  {
    id: generateId(),
    summary: '用户每天早上 9 点开始工作，习惯先查看日程和邮件',
    content:
      '通过多次对话观察，用户通常在早上 9 点左右开始工作。每天开工时习惯先查看当天的日程安排和未读邮件，然后进入开发工作。',
    conversationId: 'conv-003',
    tags: ['习惯', '工作时间', '日程'],
    createdAt: new Date(now - 3 * DAY).toISOString(),
  },
  {
    id: generateId(),
    summary: '项目使用 conventional-commits 规范，Git 分支策略为 dev/main',
    content:
      '项目 Git 提交遵循 conventional-commits 规范（feat/fix/docs/refactor/test/chore）。主要开发在 dev 分支进行，main 分支为稳定版本。使用 Husky + commitlint 强制规范。',
    conversationId: 'conv-004',
    tags: ['Git', '规范', 'conventional-commits'],
    createdAt: new Date(now - 2 * DAY).toISOString(),
  },
  {
    id: generateId(),
    summary: '用户希望宠物系统有养成玩法，不只是展示模型',
    content:
      '在讨论桌面宠物功能时，用户强调不要做成单纯的模型展示工具，要有养成玩法（喂食、清洁、心情等属性系统），让宠物有"温度"。',
    conversationId: 'conv-005',
    tags: ['宠物', '养成', '需求'],
    createdAt: new Date(now - 1 * DAY).toISOString(),
  },
  {
    id: generateId(),
    summary: '暗色模式必须支持，设计风格避免纯黑纯白',
    content:
      '设计规范要求所有模块必须支持暗色模式，使用 Ant Design ConfigProvider 暗色算法。色彩风格避免纯黑纯白，主色调为温暖橙黄系。',
    conversationId: 'conv-006',
    tags: ['设计', '暗色模式', '色彩'],
    createdAt: new Date(now - 12 * HOUR).toISOString(),
  },
]

/** 获取记忆列表（mock） */
export async function fetchMemories(
  params: { page?: number; pageSize?: number } = {}
): Promise<MemoryListResponse> {
  const { page = 1, pageSize = 20 } = params
  await simulateDelay()

  const start = (page - 1) * pageSize
  const items = mockMemories.slice(start, start + pageSize)

  return {
    items,
    total: mockMemories.length,
    page,
    pageSize,
  }
}

/** 语义搜索记忆（mock） */
export async function searchMemories(query: string): Promise<MemorySearchResult> {
  await simulateDelay(600)

  if (!query.trim()) {
    return { items: [], query }
  }

  // mock: 按关键词匹配，附带模拟相似度分数
  const lowerQuery = query.toLowerCase()
  const results: MemoryEntry[] = mockMemories
    .filter((m) => {
      const text = `${m.summary} ${m.content} ${m.tags.join(' ')}`.toLowerCase()
      return lowerQuery.split(/\s+/).some((w) => text.includes(w))
    })
    .map((m, idx) => ({
      ...m,
      similarity: Math.max(0.5, 1 - idx * 0.12 - Math.random() * 0.05),
    }))
    .sort((a, b) => (b.similarity ?? 0) - (a.similarity ?? 0))

  // 如果关键词完全没匹配到，返回相似度较低的随机结果
  if (results.length === 0) {
    const fallback = mockMemories.slice(0, 3).map((m, idx) => ({
      ...m,
      similarity: Math.max(0.3, 0.55 - idx * 0.1 - Math.random() * 0.1),
    }))
    return { items: fallback, query }
  }

  return { items: results, query }
}

/** 删除记忆（mock） */
export async function deleteMemory(id: string): Promise<void> {
  await simulateDelay(300)
  const idx = mockMemories.findIndex((m) => m.id === id)
  if (idx !== -1) {
    mockMemories.splice(idx, 1)
  }
}

/** 模拟网络延迟 */
function simulateDelay(ms = 400): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}
