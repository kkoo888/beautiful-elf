/** 技能模块类型定义 */

/** 技能使用统计 */
export interface SkillStats {
  callCount: number
  successCount: number
  failCount: number
  avgDurationMs: number
  lastCalledAt: string | null
}

/** 技能运行统计 */
export interface SkillRuntimeStats {
  callCount: number
  successCount: number
  failCount: number
  avgDurationMs: number
  lastCalledAt: string | null
}

/** 技能数据 */
export interface Skill {
  id: number
  name: string
  displayName: string
  description: string
  version: string
  source: string
  isEnabled: number
  triggerWords: string[]
  dependencies: string[]
  config: Record<string, unknown>
  stats?: SkillRuntimeStats
  createdAt: string
  updatedAt: string
}

/** 安装来源类型 */
export type InstallSource = 'file' | 'github'

/** 安装请求参数 */
export interface InstallSkillInput {
  source: InstallSource
  /** .skill 文件内容（base64）或 GitHub 仓库地址 */
  content: string
}

/** 炼化请求参数 */
export interface RefineSkillInput {
  /** 用户自定义的优化提示 */
  prompt?: string
}

/** 炼化结果 */
export interface RefineResult {
  /** LLM 生成的优化建议 */
  suggestions: string[]
  /** 优化后的 SKILL.md 内容 */
  refinedContent: string
}

/** 技能链节点 */
export interface ChainNode {
  skillId: number
  /** 执行顺序（从 0 开始） */
  order: number
}

/** 技能链配置 */
export interface SkillChain {
  id: string
  name: string
  nodes: ChainNode[]
  createdAt: string
}

/** 技能列表查询参数 */
export interface SkillQueryParams {
  page?: number
  pageSize?: number
  isEnabled?: number
}

/** 技能创建参数 */
export interface CreateSkillInput {
  name: string
  displayName: string
  description: string
  version: string
  source: string
  triggerWords: string[]
  dependencies: string[]
  config: Record<string, unknown>
}

/** 技能更新参数 */
export interface UpdateSkillInput {
  displayName?: string
  description?: string
  version?: string
  source?: string
  triggerWords?: string[]
  dependencies?: string[]
  config?: Record<string, unknown>
}

/** 分页结果 */
export interface PaginatedResult<T> {
  data: T[]
  total: number
  page: number
  pageSize: number
}
