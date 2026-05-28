/** 翻译模块类型定义 */

/** 翻译模式 */
export type TranslateMode = 'general' | 'terminology'

/** 术语命中项 */
export interface TermHit {
  /** 术语原文 */
  term: string
  /** 术语译文 */
  translation: string
}

/** 翻译结果 */
export interface TranslateResult {
  /** 唯一 ID */
  id: string
  /** 原文 */
  sourceText: string
  /** 译文 */
  targetText: string
  /** 源语言 */
  sourceLang: string
  /** 目标语言 */
  targetLang: string
  /** 翻译模式 */
  mode: TranslateMode
  /** 术语命中列表 */
  termHits?: TermHit[]
  /** 创建时间 */
  createdAt: string
}

/** 翻译请求 */
export interface TranslateRequest {
  /** 原文 */
  sourceText: string
  /** 源语言 */
  sourceLang: string
  /** 目标语言 */
  targetLang: string
  /** 翻译模式 */
  mode: TranslateMode
}

/** 翻译历史收藏请求 */
export interface FavoriteRequest {
  /** 翻译结果 ID */
  id: string
  /** 是否收藏 */
  favorite: boolean
}

/** 支持的语言 */
export interface Language {
  /** 语言代码 */
  code: string
  /** 语言名称 */
  name: string
  /** 语言名称（英文） */
  nameEn: string
}

/** 语言自动检测结果 */
export interface DetectResult {
  /** 检测到的语言代码 */
  lang: string
  /** 置信度 0-1 */
  confidence: number
}
