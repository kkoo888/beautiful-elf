import type {
  ClipboardItem,
  ClipboardListParams,
  ClipboardListResponse
} from '../types/clipboard'

// ============================================================
// Mock 数据
// ============================================================

const MOCK_ITEMS: ClipboardItem[] = [
  {
    id: '1',
    content: 'npm install react-window @types/react-window',
    contentType: 'code',
    language: 'bash',
    isPinned: true,
    copiedAt: '2026-05-28T10:30:00Z',
    createdAt: '2026-05-28T10:30:00Z'
  },
  {
    id: '2',
    content: '这是一段普通的剪贴板文本内容，用于测试显示效果。',
    contentType: 'text',
    isPinned: false,
    copiedAt: '2026-05-28T10:25:00Z',
    createdAt: '2026-05-28T10:25:00Z'
  },
  {
    id: '3',
    content: 'https://github.com/nicolestandifer3/react-window',
    contentType: 'link',
    isPinned: false,
    copiedAt: '2026-05-28T10:20:00Z',
    createdAt: '2026-05-28T10:20:00Z'
  },
  {
    id: '4',
    content: `function fibonacci(n: number): number {
  if (n <= 1) return n
  return fibonacci(n - 1) + fibonacci(n - 2)
}

console.log(fibonacci(10)) // 55`,
    contentType: 'code',
    language: 'typescript',
    isPinned: true,
    copiedAt: '2026-05-28T10:15:00Z',
    createdAt: '2026-05-28T10:15:00Z'
  },
  {
    id: '5',
    content: 'Beautiful-Elf 是一个温暖亲切的桌面宠物助手，帮你管理日常任务。',
    contentType: 'text',
    isPinned: false,
    copiedAt: '2026-05-28T10:10:00Z',
    createdAt: '2026-05-28T10:10:00Z'
  },
  {
    id: '6',
    content: 'https://ant.design/index-cn',
    contentType: 'link',
    isPinned: false,
    copiedAt: '2026-05-28T10:05:00Z',
    createdAt: '2026-05-28T10:05:00Z'
  },
  {
    id: '7',
    content: `import { create } from 'zustand'
import { persist } from 'zustand/middleware'

const useStore = create()(
  persist(
    (set) => ({
      count: 0,
      increment: () => set((s) => ({ count: s.count + 1 }))
    }),
    { name: 'my-store' }
  )
)`,
    contentType: 'code',
    language: 'typescript',
    isPinned: false,
    copiedAt: '2026-05-28T10:00:00Z',
    createdAt: '2026-05-28T10:00:00Z'
  },
  {
    id: '8',
    content: '剪贴板历史最多保留 1000 条记录，超过后自动清理最早的内容。',
    contentType: 'text',
    isPinned: false,
    copiedAt: '2026-05-28T09:55:00Z',
    createdAt: '2026-05-28T09:55:00Z'
  },
  {
    id: '9',
    content: `SELECT u.name, COUNT(o.id) AS order_count
FROM users u
LEFT JOIN orders o ON u.id = o.user_id
WHERE o.created_at > '2026-01-01'
GROUP BY u.name
HAVING order_count > 5
ORDER BY order_count DESC;`,
    contentType: 'code',
    language: 'sql',
    isPinned: false,
    copiedAt: '2026-05-28T09:50:00Z',
    createdAt: '2026-05-28T09:50:00Z'
  },
  {
    id: '10',
    content: 'Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.',
    contentType: 'text',
    isPinned: false,
    copiedAt: '2026-05-28T09:45:00Z',
    createdAt: '2026-05-28T09:45:00Z'
  }
]

// 生成更多 mock 数据
for (let i = 11; i <= 50; i++) {
  const types: ClipboardItem['contentType'][] = ['text', 'code', 'link']
  const type = types[i % 3]
  MOCK_ITEMS.push({
    id: String(i),
    content:
      type === 'link'
        ? `https://example.com/page/${i}`
        : type === 'code'
          ? `// 代码片段 #${i}\nconst value = ${i};`
          : `这是第 ${i} 条剪贴板内容，用于测试虚拟滚动性能。`,
    contentType: type,
    language: type === 'code' ? 'javascript' : undefined,
    isPinned: false,
    copiedAt: new Date(Date.now() - i * 300_000).toISOString(),
    createdAt: new Date(Date.now() - i * 300_000).toISOString()
  })
}

// 模拟网络延迟
const delay = (ms = 300) => new Promise((r) => setTimeout(r, ms))

// ============================================================
// API 函数（mock 实现，后续替换为真实 API）
// ============================================================

/** 获取剪贴板列表 */
export async function fetchClipboardList(
  params: ClipboardListParams = {}
): Promise<ClipboardListResponse> {
  const { page = 1, pageSize = 20, keyword } = params
  await delay()

  let filtered = [...MOCK_ITEMS]
  if (keyword) {
    const lower = keyword.toLowerCase()
    filtered = filtered.filter((item) =>
      item.content.toLowerCase().includes(lower)
    )
  }

  // 固定项排在最前
  filtered.sort((a, b) => {
    if (a.isPinned !== b.isPinned) return a.isPinned ? -1 : 1
    return new Date(b.copiedAt).getTime() - new Date(a.copiedAt).getTime()
  })

  const start = (page - 1) * pageSize
  return {
    items: filtered.slice(start, start + pageSize),
    total: filtered.length,
    page,
    pageSize
  }
}

/** 新增剪贴板条目 */
export async function createClipboardItem(
  data: Pick<ClipboardItem, 'content' | 'contentType' | 'language'>
): Promise<ClipboardItem> {
  await delay()
  const now = new Date().toISOString()
  const item: ClipboardItem = {
    id: String(Date.now()),
    content: data.content,
    contentType: data.contentType,
    language: data.language,
    isPinned: false,
    copiedAt: now,
    createdAt: now
  }
  MOCK_ITEMS.unshift(item)
  return item
}

/** 删除剪贴板条目 */
export async function deleteClipboardItem(id: string): Promise<void> {
  await delay()
  const idx = MOCK_ITEMS.findIndex((item) => item.id === id)
  if (idx !== -1) MOCK_ITEMS.splice(idx, 1)
}

/** 固定/取消固定 */
export async function togglePinClipboardItem(
  id: string
): Promise<ClipboardItem> {
  await delay()
  const item = MOCK_ITEMS.find((i) => i.id === id)
  if (!item) throw new Error(`ClipboardItem ${id} not found`)
  item.isPinned = !item.isPinned
  return { ...item }
}
