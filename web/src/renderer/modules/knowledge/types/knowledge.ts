import type { KnowledgeDocument } from '@/types'

// 重导出全局类型，方便模块内使用
export type { KnowledgeDocument }

/** 文档状态枚举（后端 int） */
export const STATUS_MAP: Record<number, { label: string; color: string }> = {
  0: { label: '待处理', color: 'default' },
  1: { label: '处理中', color: 'processing' },
  2: { label: '就绪', color: 'success' },
  3: { label: '失败', color: 'error' },
}

/** 文件类型图标（对齐 SimpleDirectoryReader 内置支持格式） */
export const FILE_TYPE_ICONS: Record<string, string> = {
  pdf: '📄',
  docx: '📝',
  pptx: '📊',
  xlsx: '📗',
  xls: '📗',
  csv: '📊',
  json: '🔧',
  html: '🌐',
  md: '📑',
  txt: '📃',
  epub: '📚',
  ipynb: '📒',
}

/** 支持的文件扩展名（对齐 SimpleDirectoryReader 内置 reader） */
export const SUPPORTED_EXTENSIONS = [
  '.pdf', '.docx', '.pptx',
  '.xlsx', '.xls',
  '.csv', '.json', '.html',
  '.md', '.txt',
  '.epub', '.ipynb',
]

/** 最大文件大小 (200MB) */
export const MAX_FILE_SIZE = 200 * 1024 * 1024
