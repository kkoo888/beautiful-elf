import type {
  KnowledgeDocument,
  KnowledgeChunk,
  DocumentListParams,
  PaginatedResponse,
} from '../types/knowledge'

// ── Mock 数据 ─────────────────────────────────────────────────────────────

const mockDocuments: KnowledgeDocument[] = [
  {
    id: '1',
    fileName: '产品需求文档.pdf',
    fileType: 'pdf',
    chunkCount: 42,
    status: 'ready',
    deleted: false,
    createdAt: '2026-05-20T10:00:00Z',
    updatedAt: '2026-05-20T10:05:00Z',
  },
  {
    id: '2',
    fileName: 'API接口文档.md',
    fileType: 'md',
    chunkCount: 18,
    status: 'ready',
    deleted: false,
    createdAt: '2026-05-21T14:30:00Z',
    updatedAt: '2026-05-21T14:32:00Z',
  },
  {
    id: '3',
    fileName: '用户手册.docx',
    fileType: 'docx',
    chunkCount: 56,
    status: 'ready',
    deleted: false,
    createdAt: '2026-05-22T09:15:00Z',
    updatedAt: '2026-05-22T09:20:00Z',
  },
  {
    id: '4',
    fileName: '数据库设计.yaml',
    fileType: 'yaml',
    chunkCount: 12,
    status: 'indexing',
    deleted: false,
    createdAt: '2026-05-25T16:00:00Z',
    updatedAt: '2026-05-25T16:00:00Z',
  },
  {
    id: '5',
    fileName: '旧版配置.json',
    fileType: 'json',
    chunkCount: 0,
    status: 'error',
    deleted: true,
    createdAt: '2026-05-18T08:00:00Z',
    updatedAt: '2026-05-24T12:00:00Z',
  },
  {
    id: '6',
    fileName: '会议纪要.txt',
    fileType: 'txt',
    chunkCount: 8,
    status: 'ready',
    deleted: true,
    createdAt: '2026-05-19T11:00:00Z',
    updatedAt: '2026-05-25T09:00:00Z',
  },
]

const mockChunks: Record<string, KnowledgeChunk[]> = {
  '1': [
    {
      id: 'c1',
      documentId: '1',
      chunkIndex: 0,
      content:
        '## 1. 项目概述\n\n本项目旨在构建一个智能桌面助手应用，集成 AI 对话、日程管理、知识库等功能。',
    },
    {
      id: 'c2',
      documentId: '1',
      chunkIndex: 1,
      content:
        '## 2. 核心功能\n\n- AI 对话：支持多轮对话、流式输出\n- 日程管理：日历视图、提醒通知\n- 知识库：文档导入、语义搜索',
    },
    {
      id: 'c3',
      documentId: '1',
      chunkIndex: 2,
      content:
        '## 3. 技术架构\n\n前端采用 Electron + React，后端使用 Node.js + PostgreSQL，AI 部分集成 Ollama 本地模型。',
    },
    {
      id: 'c4',
      documentId: '1',
      chunkIndex: 3,
      content:
        '## 4. 用户故事\n\n作为一名用户，我希望能够导入自己的文档到知识库中，这样 AI 就能基于我的私有知识回答问题。',
    },
  ],
  '2': [
    {
      id: 'c5',
      documentId: '2',
      chunkIndex: 0,
      content: '# API 接口文档\n\n## 基础信息\n- Base URL: `/api/v1`\n- 认证方式: Bearer Token',
    },
    {
      id: 'c6',
      documentId: '2',
      chunkIndex: 1,
      content:
        '## 对话接口\n\n### POST /chat/completions\n创建新的对话补全请求。\n\n**参数：**\n- `messages`: 消息列表\n- `model`: 模型名称',
    },
  ],
  '3': [
    {
      id: 'c7',
      documentId: '3',
      chunkIndex: 0,
      content: '# 用户手册\n\n欢迎使用 Beautiful-Elf 桌面助手！本手册将帮助您快速上手。',
    },
    {
      id: 'c8',
      documentId: '3',
      chunkIndex: 1,
      content: '## 快速开始\n\n1. 下载安装包\n2. 双击运行\n3. 完成初始设置\n4. 开始使用 AI 助手',
    },
  ],
}

// ── Mock API 工具 ──────────────────────────────────────────────────────────

function delay(ms = 300): Promise<void> {
  return new Promise((r) => setTimeout(r, ms))
}

function generateId(): string {
  return Math.random().toString(36).slice(2, 10)
}

// ── API 函数 ──────────────────────────────────────────────────────────────

/** 获取文档列表 */
export async function fetchDocuments(
  params: DocumentListParams = {}
): Promise<PaginatedResponse<KnowledgeDocument>> {
  await delay()

  const { page = 1, pageSize = 10, keyword, fileType, deleted = false } = params

  let filtered = mockDocuments.filter((d) => d.isDeleted === deleted)

  if (keyword) {
    const kw = keyword.toLowerCase()
    filtered = filtered.filter((d) => d.fileName.toLowerCase().includes(kw))
  }

  if (fileType) {
    filtered = filtered.filter((d) => d.fileType === fileType)
  }

  const total = filtered.length
  const start = (page - 1) * pageSize
  const data = filtered.slice(start, start + pageSize)

  return { data, total, page, pageSize }
}

/** 上传文档（mock：模拟创建一条记录） */
export async function uploadDocument(file: File): Promise<KnowledgeDocument> {
  await delay(800)

  const ext = file.name.split('.').pop()?.toLowerCase() ?? 'txt'
  const doc: KnowledgeDocument = {
    id: generateId(),
    fileName: file.name,
    fileType: ext as KnowledgeDocument['fileType'],
    chunkCount: 0,
    status: 'indexing',
    deleted: false,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  }

  mockDocuments.unshift(doc)

  // 模拟索引完成
  setTimeout(() => {
    doc.status = 'ready'
    doc.chunkCount = Math.floor(Math.random() * 30) + 5
    doc.updatedAt = new Date().toISOString()
  }, 2000)

  return doc
}

/** 软删除文档 */
export async function deleteDocument(id: string): Promise<void> {
  await delay()

  const doc = mockDocuments.find((d) => d.id === id)
  if (doc) {
    doc.isDeleted = true
    doc.updatedAt = new Date().toISOString()
  }
}

/** 恢复文档 */
export async function restoreDocument(id: string): Promise<void> {
  await delay()

  const doc = mockDocuments.find((d) => d.id === id)
  if (doc) {
    doc.isDeleted = false
    doc.updatedAt = new Date().toISOString()
  }
}

/** 获取文档分块列表 */
export async function fetchChunks(documentId: string): Promise<KnowledgeChunk[]> {
  await delay()

  return mockChunks[documentId] ?? []
}

/** 导出知识库 */
export async function exportKnowledge(): Promise<Blob> {
  await delay(500)

  const exportData = {
    exportedAt: new Date().toISOString(),
    documents: mockDocuments.filter((d) => !d.isDeleted),
    chunks: Object.values(mockChunks).flat(),
  }

  return new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' })
}
