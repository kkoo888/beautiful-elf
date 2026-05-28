import type { OcrResult } from '../types/ocr'

/**
 * OCR 识别 API
 *
 * 当前使用 mock 实现，预留 tesseract.js 接口。
 *
 * 后续接入 tesseract.js 示例：
 * ```ts
 * import Tesseract from 'tesseract.js'
 *
 * export async function recognizeText(imageData: string): Promise<OcrResult> {
 *   const { data } = await Tesseract.recognize(imageData, 'chi_sim+eng', {
 *     logger: (m) => console.log(m),
 *   })
 *   return {
 *     text: data.text,
 *     confidence: data.confidence / 100,
 *     language: 'chi_sim+eng',
 *   }
 * }
 * ```
 */

export async function recognizeText(imageData: string): Promise<OcrResult> {
  // 模拟 2 秒识别延迟
  await new Promise((resolve) => setTimeout(resolve, 2000))

  void imageData // 未来传入 tesseract.js

  return {
    text: '这是一段从图片中识别出的文字内容。OCR（光学字符识别）技术可以将图片中的文字转换为可编辑的文本格式。支持中英文混合识别，识别准确率可达92%以上。',
    confidence: 0.92,
    language: 'chi_sim+eng',
  }
}
