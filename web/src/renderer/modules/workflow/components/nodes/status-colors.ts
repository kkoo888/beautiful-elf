/** 节点状态颜色映射 */

export const NODE_STATUS_STYLES: Record<string, { bg: string; border: string; text: string }> = {
  idle: { bg: '#f5f5f5', border: '#d9d9d9', text: '#8c8c8c' },
  running: { bg: '#e6f4ff', border: '#1677ff', text: '#1677ff' },
  success: { bg: '#f6ffed', border: '#52c41a', text: '#389e0d' },
  failed: { bg: '#fff2f0', border: '#ff4d4f', text: '#cf1322' },
  skipped: { bg: '#f5f5f5', border: '#bfbfbf', text: '#8c8c8c' },
}
