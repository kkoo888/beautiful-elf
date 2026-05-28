import type { CaptureMode, CaptureResult, AnalysisMode, AnalysisResult } from '../types/visual'

function generateId(): string {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 8)
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

/**
 * 用 Canvas 生成占位截图（base64）
 * 真实环境替换为 Electron desktopCapturer
 */
export async function captureScreen(mode: CaptureMode): Promise<CaptureResult> {
  await delay(1500)

  const width = mode === 'fullscreen' ? 1280 : 640
  const height = mode === 'fullscreen' ? 720 : 480

  const canvas = document.createElement('canvas')
  canvas.width = width
  canvas.height = height
  const ctx = canvas.getContext('2d')!

  // 背景
  ctx.fillStyle = '#1e1e2e'
  ctx.fillRect(0, 0, width, height)

  // 模拟编辑器区域
  ctx.fillStyle = '#313244'
  ctx.fillRect(40, 40, width - 80, height - 80)

  // 代码行
  ctx.fillStyle = '#89b4fa'
  ctx.font = '14px monospace'
  const lines = [
    'import React from "react"',
    '',
    'export function List({ items }: { items: string[] }) {',
    '  return (',
    '    <ul>',
    '      {items.map((item, i) => (',
    '        <li key={i}>{item}</li>',
    '      ))}',
    '    </ul>',
    '  )',
    '}',
  ]
  lines.forEach((line, i) => {
    ctx.fillStyle = i === 0 ? '#a6e3a1' : '#cdd6f4'
    ctx.fillText(line, 60, 80 + i * 22)
  })

  // 光标闪烁
  ctx.fillStyle = '#f5e0dc'
  ctx.fillRect(210, 80 + 22 * 5, 2, 18)

  // 标注模式
  ctx.fillStyle = '#f38ba8'
  ctx.font = 'bold 16px sans-serif'
  ctx.fillText(`[${mode === 'fullscreen' ? '全屏截图' : '选区截图'}]`, 50, height - 20)

  const imageData = canvas.toDataURL('image/png')

  return {
    id: generateId(),
    imageData,
    timestamp: Date.now(),
    mode,
  }
}

/**
 * Mock 分析图片内容
 */
export async function analyzeImage(
  imageData: string,
  mode: AnalysisMode
): Promise<AnalysisResult> {
  await delay(1500)

  const mockResults: Record<AnalysisMode, { result: string; confidence: number }> = {
    general: {
      result: '屏幕上显示了一个代码编辑器，正在编写 React 组件。代码结构清晰，使用了 TypeScript 泛型和 JSX 语法。',
      confidence: 0.92,
    },
    text: {
      result: `import React from 'react'\n\nexport function List({ items }: { items: string[] }) {\n  return (\n    <ul>\n      {items.map((item, i) => (\n        <li key={i}>{item}</li>\n      ))}\n    </ul>\n  )\n}`,
      confidence: 0.97,
    },
    code: {
      result: '检测到 TypeScript 代码，正在实现一个列表组件。使用了 React 函数组件 + Hooks 模式，props 类型使用泛型定义，渲染逻辑简洁。',
      confidence: 0.89,
    },
  }

  const { result, confidence } = mockResults[mode]

  return {
    id: generateId(),
    captureId: '', // 由调用方填充
    mode,
    result,
    confidence,
  }
}
