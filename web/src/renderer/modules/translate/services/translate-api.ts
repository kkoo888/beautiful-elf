/** 翻译 API 服务（Mock 实现） */

import type {
  TranslateRequest,
  TranslateResult,
  FavoriteRequest,
  DetectResult,
  Language
} from '../types/translate'

/** 模拟延迟 */
const delay = (ms: number): Promise<void> =>
  new Promise((resolve) => setTimeout(resolve, ms))

/** 生成唯一 ID */
const generateId = (): string => crypto.randomUUID()

// ─── 支持的语言列表 ──────────────────────────────────────

const SUPPORTED_LANGUAGES: Language[] = [
  { code: 'auto', name: '自动检测', nameEn: 'Auto Detect' },
  { code: 'zh', name: '中文', nameEn: 'Chinese' },
  { code: 'en', name: '英语', nameEn: 'English' },
  { code: 'ja', name: '日语', nameEn: 'Japanese' },
  { code: 'ko', name: '韩语', nameEn: 'Korean' },
  { code: 'fr', name: '法语', nameEn: 'French' },
  { code: 'de', name: '德语', nameEn: 'German' },
  { code: 'es', name: '西班牙语', nameEn: 'Spanish' },
  { code: 'ru', name: '俄语', nameEn: 'Russian' },
  { code: 'pt', name: '葡萄牙语', nameEn: 'Portuguese' },
  { code: 'ar', name: '阿拉伯语', nameEn: 'Arabic' },
  { code: 'it', name: '意大利语', nameEn: 'Italian' }
]

// ─── Mock 术语库 ─────────────────────────────────────────

const MOCK_TERM_DB: Record<string, { term: string; translation: string }[]> = {
  zh: [
    { term: '机器学习', translation: 'Machine Learning' },
    { term: '神经网络', translation: 'Neural Network' },
    { term: '深度学习', translation: 'Deep Learning' },
    { term: '自然语言处理', translation: 'Natural Language Processing' },
    { term: '大语言模型', translation: 'Large Language Model' },
    { term: '知识图谱', translation: 'Knowledge Graph' },
    { term: '向量数据库', translation: 'Vector Database' },
    { term: '微调', translation: 'Fine-tuning' },
    { term: '提示词工程', translation: 'Prompt Engineering' },
    { term: '多模态', translation: 'Multimodal' }
  ],
  en: [
    { term: 'Machine Learning', translation: '机器学习' },
    { term: 'Neural Network', translation: '神经网络' },
    { term: 'Deep Learning', translation: '深度学习' },
    { term: 'Large Language Model', translation: '大语言模型' },
    { term: 'Prompt Engineering', translation: '提示词工程' },
    { term: 'Fine-tuning', translation: '微调' },
    { term: 'Retrieval-Augmented Generation', translation: '检索增强生成' },
    { term: 'Transformer', translation: 'Transformer 架构' },
    { term: 'Embedding', translation: '向量嵌入' },
    { term: 'Token', translation: '词元' }
  ]
}

// ─── Mock 翻译响应 ──────────────────────────────────────

const MOCK_TRANSLATIONS: Record<string, Record<string, string>> = {
  'zh-en': 'Hello! This is a mock translation result. The system uses advanced AI models for high-quality translation.',
  'en-zh': '你好！这是一个模拟翻译结果。系统使用先进的 AI 模型进行高质量翻译。',
  'zh-ja': 'こんにちは！これはモック翻訳結果です。システムは高度なAIモデルを使用して高品質な翻訳を行います。',
  'ja-zh': '你好！这是模拟翻译结果。系统使用先进的AI模型进行高质量翻译。',
  'zh-ko': '안녕하세요! 이것은 모의 번역 결과입니다. 시스템은 첨단 AI 모델을 사용하여 고품질 번역을 제공합니다.',
  'ko-zh': '你好！这是模拟翻译结果。系统使用先进的AI模型进行高质量翻译。',
  'en-ja': 'こんにちは！これはモック翻訳結果です。システムは高度なAIモデルを使用しています。',
  'ja-en': 'Hello! This is a mock translation result. The system uses advanced AI models.',
  'en-fr': "Bonjour ! Ceci est un résultat de traduction simulé. Le système utilise des modèles d'IA avancés pour une traduction de haute qualité.",
  'fr-en': 'Hello! This is a mock translation result. The system uses advanced AI models for high-quality translation.',
  'en-de': 'Hallo! Dies ist ein simuliertes Übersetzungsergebnis. Das System verwendet fortschrittliche KI-Modelle für qualitativ hochwertige Übersetzungen.',
  'de-en': 'Hello! This is a mock translation result. The system uses advanced AI models for high-quality translation.'
}

/** Mock 翻译历史 */
let mockHistory: TranslateResult[] = [
  {
    id: generateId(),
    sourceText: '机器学习是人工智能的一个重要分支',
    targetText:
      'Machine Learning is an important branch of artificial intelligence',
    sourceLang: 'zh',
    targetLang: 'en',
    mode: 'terminology',
    termHits: [{ term: '机器学习', translation: 'Machine Learning' }],
    createdAt: new Date(Date.now() - 3600_000).toISOString()
  },
  {
    id: generateId(),
    sourceText: 'Hello, how are you today?',
    targetText: '你好，你今天怎么样？',
    sourceLang: 'en',
    targetLang: 'zh',
    mode: 'general',
    createdAt: new Date(Date.now() - 7200_000).toISOString()
  },
  {
    id: generateId(),
    sourceText: '深度学习模型需要大量的训练数据',
    targetText:
      'Deep learning models require a large amount of training data',
    sourceLang: 'zh',
    targetLang: 'en',
    mode: 'terminology',
    termHits: [{ term: '深度学习', translation: 'Deep Learning' }],
    createdAt: new Date(Date.now() - 86400_000).toISOString()
  }
]

// ─── API 函数 ────────────────────────────────────────────

/** 获取支持的语言列表 */
export async function fetchLanguages(): Promise<Language[]> {
  await delay(100)
  return SUPPORTED_LANGUAGES
}

/** 自动检测语言 */
export async function detectLanguage(text: string): Promise<DetectResult> {
  await delay(200 + Math.random() * 300)

  // 简单规则匹配模拟
  const chineseRegex = /[\u4e00-\u9fff]/
  const japaneseRegex = /[\u3040-\u30ff]/
  const koreanRegex = /[\uac00-\ud7af]/
  const arabicRegex = /[\u0600-\u06ff]/
  const russianRegex = /[\u0400-\u04ff]/

  if (chineseRegex.test(text)) return { lang: 'zh', confidence: 0.95 }
  if (japaneseRegex.test(text)) return { lang: 'ja', confidence: 0.92 }
  if (koreanRegex.test(text)) return { lang: 'ko', confidence: 0.9 }
  if (arabicRegex.test(text)) return { lang: 'ar', confidence: 0.88 }
  if (russianRegex.test(text)) return { lang: 'ru', confidence: 0.85 }

  // 默认英文
  return { lang: 'en', confidence: 0.8 }
}

/** 执行翻译 */
export async function translate(
  request: TranslateRequest
): Promise<TranslateResult> {
  await delay(600 + Math.random() * 1200)

  const { sourceText, sourceLang, targetLang, mode } = request

  // 处理 auto 检测
  const actualSourceLang =
    sourceLang === 'auto'
      ? (await detectLanguage(sourceText)).lang
      : sourceLang

  // 查找翻译
  const key = `${actualSourceLang}-${targetLang}`
  let targetText =
    MOCK_TRANSLATIONS[key] ??
    `[${targetLang}] ${sourceText}`

  // 如果原文较短，直接拼接模拟
  if (sourceText.length < 20 && !MOCK_TRANSLATIONS[key]) {
    targetText = `(${targetLang}) ${sourceText}`
  }

  // 术语模式：检查术语库
  const termHits: { term: string; translation: string }[] = []
  if (mode === 'terminology') {
    const terms = MOCK_TERM_DB[actualSourceLang] ?? []
    for (const t of terms) {
      if (sourceText.includes(t.term)) {
        termHits.push(t)
      }
    }
  }

  const result: TranslateResult = {
    id: generateId(),
    sourceText,
    targetText,
    sourceLang: actualSourceLang,
    targetLang,
    mode,
    termHits: termHits.length > 0 ? termHits : undefined,
    createdAt: new Date().toISOString()
  }

  // 存入历史
  mockHistory = [result, ...mockHistory].slice(0, 50)

  return result
}

/** 获取翻译历史 */
export async function fetchHistory(): Promise<TranslateResult[]> {
  await delay(300 + Math.random() * 300)
  return [...mockHistory]
}

/** 收藏/取消收藏翻译结果 */
export async function toggleFavorite(
  request: FavoriteRequest
): Promise<{ success: boolean }> {
  await delay(200 + Math.random() * 200)
  console.log('[Mock] Toggle favorite:', request)
  return { success: true }
}
