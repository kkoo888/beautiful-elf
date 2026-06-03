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
export type InstallSource = 'folder' | 'github'

/** 风险等级 */
export type RiskLevel = 'critical' | 'high' | 'medium' | 'low' | 'info'

/** 扫描判定结果 */
export type ScanVerdict = 'safe' | 'caution' | 'danger'

/** 单条扫描问题 */
export interface ScanIssue {
  /** 风险等级 */
  level: RiskLevel
  /** 检测类别 */
  category: string
  /** 问题描述（中文） */
  message: string
  /** 命中的文件路径 */
  file?: string
  /** 命中的行号 */
  line?: number
  /** 命中的原始内容（截取片段） */
  snippet?: string
}

/** 安全扫描结果 */
export interface ScanResult {
  /** 扫描的文件数 */
  fileCount: number
  /** 问题列表 */
  issues: ScanIssue[]
  /** 各级别计数 */
  summary: {
    critical: number
    high: number
    medium: number
    low: number
    info: number
  }
  /** 综合判定 */
  verdict: ScanVerdict
}

/** 文件夹解析结果（选完文件夹后、确认安装前的中间状态） */
export interface SkillFolderParsed {
  /** 文件夹名（默认作为技能名称） */
  folderName: string
  /** SKILL.md 中提取的 name */
  extractedName?: string
  /** SKILL.md 中提取的 description */
  extractedDescription?: string
  /** metadata.json 中提取的 version */
  extractedVersion?: string
  /** SKILL.md 中提取的触发词 */
  extractedTriggerWords?: string[]
  /** metadata.json 中提取的依赖 */
  extractedDependencies?: string[]
  /** 文件夹内文件列表（路径 + 内容） */
  files: { path: string; content: string }[]
  /** 安全扫描结果 */
  scanResult: ScanResult
}

/** 安装请求参数 */
export interface InstallSkillInput {
  source: InstallSource
  /** 技能名称（文件夹名，用户可改） */
  name: string
  /** 显示名称 */
  displayName?: string
  /** 技能简介 */
  description: string
  /** 版本号 */
  version?: string
  /** 触发词 */
  triggerWords?: string[]
  /** 依赖技能 */
  dependencies?: string[]
  /** 文件夹内容（base64 zip）或 GitHub 仓库地址 */
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
