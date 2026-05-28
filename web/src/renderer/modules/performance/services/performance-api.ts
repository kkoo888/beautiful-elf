/** 性能监控 API 服务（mock 实现） */

import type { PerformanceMetric } from '../types/performance'

/** 生成指定范围内的随机数 */
function randomInRange(min: number, max: number): number {
  return Number((Math.random() * (max - min) + min).toFixed(1))
}

/** 生成 mock 性能数据（最近 30 个数据点，间隔 5 秒） */
export async function fetchPerformanceMetrics(): Promise<PerformanceMetric[]> {
  // 模拟网络延迟
  await new Promise((r) => setTimeout(r, 200))

  const now = Date.now()
  const points: PerformanceMetric[] = []

  // 基准值，模拟小幅波动
  let cpuBase = 45
  let memoryBase = 60
  let diskBase = 58

  for (let i = 29; i >= 0; i--) {
    // 在基准值附近波动
    cpuBase = Math.max(25, Math.min(75, cpuBase + (Math.random() - 0.48) * 8))
    memoryBase = Math.max(35, Math.min(82, memoryBase + (Math.random() - 0.47) * 5))
    diskBase = Math.max(48, Math.min(72, diskBase + (Math.random() - 0.5) * 3))

    points.push({
      cpu: randomInRange(cpuBase - 5, cpuBase + 5),
      memory: randomInRange(memoryBase - 4, memoryBase + 4),
      disk: randomInRange(diskBase - 2, diskBase + 2),
      gpu: randomInRange(20, 60),
      timestamp: new Date(now - i * 5000).toISOString(),
    })
  }

  return points
}
