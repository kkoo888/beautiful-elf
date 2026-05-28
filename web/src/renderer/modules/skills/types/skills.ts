/** 技能模块类型定义 */

/** 技能使用统计 */
export interface SkillStats {
  callCount: number
  successRate: number
  avgDuration: number
}

/** 技能数据 */
export interface Skill {
  id: string
  name: string
  description: string
  version: string
  enabled: boolean
  triggerWords: string[]
  dependencies: string[]
  stats: SkillStats
  createdAt: string
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
  skillId: string
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
  keyword?: string
  enabledOnly?: boolean
}
