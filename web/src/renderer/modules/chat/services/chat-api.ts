/** 聊天 API 服务（Mock 实现） */

import type {
  ChatRequest,
  ChatResponse,
  FeedbackRequest,
  FeedbackResponse,
  StreamToken
} from '../types/chat'

/** 模拟延迟 */
const delay = (ms: number): Promise<void> => new Promise((resolve) => setTimeout(resolve, ms))

/** Mock 响应内容池 */
const MOCK_RESPONSES: string[] = [
  '你好！有什么可以帮你的吗？ 😊',
  '这是一个很好的问题！让我来帮你分析一下。\n\n**关键点：**\n1. 首先需要理解需求\n2. 然后拆解任务\n3. 最后逐步实现',
  '根据我的理解，这里有几个方案：\n\n- **方案 A**：简单直接\n- **方案 B**：更灵活但复杂\n- **方案 C**：平衡方案\n\n推荐方案 C，兼顾了简洁和灵活性。',
  '```typescript\nfunction greet(name: string): string {\n  return `Hello, ${name}!`\n}\n\nconsole.log(greet("Beautiful-Elf"))\n```\n\n这段代码展示了基本的 TypeScript 函数定义。',
  '让我想想... 🤔\n\n这个问题涉及到几个方面：\n\n> 设计原则：单一职责、开闭原则、依赖倒置\n\n建议先从最简单的实现开始，逐步迭代优化。'
]

/** Mock 意图路由模块池 */
const MOCK_MODULES = ['schedule', 'clipboard', 'knowledge', 'translate', 'skills']

/**
 * 发送非流式聊天请求（Mock）
 */
export async function chat(request: ChatRequest): Promise<ChatResponse> {
  await delay(800 + Math.random() * 1200)

  const responseIndex = Math.floor(Math.random() * MOCK_RESPONSES.length)
  const isCached = Math.random() > 0.7
  const intentRoute =
    Math.random() > 0.6
      ? {
          module: MOCK_MODULES[Math.floor(Math.random() * MOCK_MODULES.length)],
          confidence: 0.7 + Math.random() * 0.3
        }
      : undefined

  return {
    id: crypto.randomUUID(),
    content: MOCK_RESPONSES[responseIndex],
    isCached,
    intentRoute,
    model: 'qwen2.5:7b'
  }
}

/**
 * 创建流式聊天连接（Mock WebSocket）
 * 通过回调逐个返回 token
 */
export function chatStream(
  request: ChatRequest,
  onToken: (token: StreamToken) => void,
  onError?: (error: Error) => void
): { abort: () => void } {
  let aborted = false
  const messageId = crypto.randomUUID()
  const responseIndex = Math.floor(Math.random() * MOCK_RESPONSES.length)
  const fullContent = MOCK_RESPONSES[responseIndex]
  const chars = [...fullContent]

  const stream = async (): Promise<void> => {
    try {
      // 模拟首 token 延迟
      await delay(300)

      for (let i = 0; i < chars.length; i++) {
        if (aborted) break

        onToken({
          content: chars[i],
          done: false,
          messageId: i === 0 ? messageId : undefined
        })

        // 模拟逐字延迟
        await delay(20 + Math.random() * 40)
      }

      if (!aborted) {
        onToken({
          content: '',
          done: true,
          messageId: undefined
        })
      }
    } catch (err) {
      if (!aborted && onError) {
        onError(err instanceof Error ? err : new Error(String(err)))
      }
    }
  }

  stream()

  return {
    abort: () => {
      aborted = true
    }
  }
}

/**
 * 提交反馈（Mock）
 */
export async function submitFeedback(
  request: FeedbackRequest
): Promise<FeedbackResponse> {
  await delay(300 + Math.random() * 500)
  console.log('[Mock] Feedback submitted:', request)
  return { success: true }
}
