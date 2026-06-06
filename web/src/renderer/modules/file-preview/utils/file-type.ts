import type { FilePreviewType } from '../types/file-preview'

const extensionMap: Record<string, FilePreviewType> = {
  '.txt': 'text',
  '.md': 'text',
  '.json': 'text',
  '.yaml': 'text',
  '.yml': 'text',
  '.js': 'code',
  '.ts': 'code',
  '.py': 'code',
  '.html': 'code',
  '.css': 'code',
  '.jsx': 'code',
  '.tsx': 'code',
  '.java': 'code',
  '.go': 'code',
  '.rs': 'code',
  '.vue': 'code',
  '.jpg': 'image',
  '.jpeg': 'image',
  '.png': 'image',
  '.gif': 'image',
  '.webp': 'image',
  '.svg': 'image',
  '.pdf': 'pdf',
}

export function getFilePreviewType(filename: string): FilePreviewType {
  const dotIndex = filename.lastIndexOf('.')
  if (dotIndex === -1) return 'unknown'
  const ext = filename.slice(dotIndex).toLowerCase()
  return extensionMap[ext] ?? 'unknown'
}
