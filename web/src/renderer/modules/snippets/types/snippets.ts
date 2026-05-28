/** 代码片段 */
export interface Snippet {
  id: string
  title: string
  content: string
  language: string
  tags: string[]
  useCount: number
  createdAt: string
  updatedAt: string
}

/** 创建/更新片段参数 */
export interface SnippetFormData {
  title: string
  content: string
  language: string
  tags: string[]
}

/** 片段查询参数 */
export interface SnippetQueryParams {
  keyword?: string
  tags?: string[]
  page?: number
  pageSize?: number
}

/** 片段列表响应 */
export interface SnippetListResponse {
  items: Snippet[]
  total: number
  page: number
  pageSize: number
}

/** 支持的语言列表 */
export const LANGUAGE_OPTIONS = [
  { value: 'javascript', label: 'JavaScript' },
  { value: 'typescript', label: 'TypeScript' },
  { value: 'python', label: 'Python' },
  { value: 'html', label: 'HTML' },
  { value: 'css', label: 'CSS' },
  { value: 'json', label: 'JSON' },
  { value: 'markdown', label: 'Markdown' },
  { value: 'sql', label: 'SQL' },
  { value: 'shell', label: 'Shell' },
  { value: 'java', label: 'Java' },
  { value: 'go', label: 'Go' },
  { value: 'rust', label: 'Rust' },
  { value: 'c', label: 'C' },
  { value: 'cpp', label: 'C++' },
  { value: 'yaml', label: 'YAML' },
  { value: 'xml', label: 'XML' },
  { value: 'php', label: 'PHP' },
  { value: 'ruby', label: 'Ruby' },
  { value: 'swift', label: 'Swift' },
  { value: 'kotlin', label: 'Kotlin' },
] as const

/** 标签颜色映射 */
export const TAG_COLORS = [
  'orange',
  'blue',
  'green',
  'purple',
  'cyan',
  'magenta',
  'gold',
  'lime',
] as const

/** 根据标签名生成固定颜色 */
export function getTagColor(tag: string): string {
  let hash = 0
  for (let i = 0; i < tag.length; i++) {
    hash = tag.charCodeAt(i) + ((hash << 5) - hash)
  }
  return TAG_COLORS[Math.abs(hash) % TAG_COLORS.length]
}
