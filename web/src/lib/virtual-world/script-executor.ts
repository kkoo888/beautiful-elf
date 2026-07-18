/**
 * 构建脚本执行引擎 (T4)
 * 对齐设计文档 §5 脚本格式
 *
 * 解析 JSON 构建脚本，按顺序调用 SceneBuilder 执行每个动作。
 * 支持的动作类型：place_block, remove_block, set_lighting, set_terrain
 */

// ── 脚本结构定义 ──

export interface BuildAction {
  tool: 'place_block' | 'remove_block' | 'set_lighting' | 'set_terrain'
  params: Record<string, unknown>
}

export interface BuildScript {
  version: string
  name: string
  description: string
  actions: BuildAction[]
}

// ── SceneBuilder 接口（对齐 scene-builder.ts，解耦具体实现）──

export interface SceneBuilder {
  placeBlock(
    x: number,
    y: number,
    z: number,
    blockId: string,
    material?: string,
    rotationY?: number,
  ): void | Promise<void>

  removeBlock(x: number, y: number, z: number): void | Promise<void>

  setLighting(
    timeOfDay: number,
    style?: string,
    ambientColor?: string,
  ): void | Promise<void>

  setTerrain(
    xMin: number,
    zMin: number,
    xMax: number,
    zMax: number,
    biome: string,
  ): void | Promise<void>
}

// ── 参数校验工具 ──

function requireFields(params: Record<string, unknown>, fields: string[]): void {
  for (const f of fields) {
    if (params[f] === undefined || params[f] === null) {
      throw new Error(`缺少必要参数: ${f}`)
    }
  }
}

function toNum(v: unknown, name: string): number {
  const n = Number(v)
  if (Number.isNaN(n)) throw new Error(`参数 ${name} 必须是数字，收到: ${v}`)
  return n
}

function toStr(v: unknown, name: string): string {
  if (typeof v !== 'string') throw new Error(`参数 ${name} 必须是字符串，收到: ${v}`)
  return v
}

// ── ScriptExecutor ──

export class ScriptExecutor {
  constructor(private readonly builder: SceneBuilder) {}

  /**
   * 执行完整构建脚本，按 actions 顺序逐个执行。
   * 任一动作失败则中止并抛出错误（fail-fast）。
   */
  async execute(script: BuildScript): Promise<void> {
    if (!script.actions?.length) return

    for (let i = 0; i < script.actions.length; i++) {
      try {
        await this.executeAction(script.actions[i])
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err)
        throw new Error(
          `脚本 "${script.name}" 执行失败（动作 #${i}, tool=${script.actions[i].tool}）: ${msg}`,
        )
      }
    }
  }

  /**
   * 执行单个构建动作，根据 tool 类型分发到对应的 SceneBuilder 方法。
   */
  async executeAction(action: BuildAction): Promise<void> {
    switch (action.tool) {
      case 'place_block':
        return this.handlePlaceBlock(action.params)
      case 'remove_block':
        return this.handleRemoveBlock(action.params)
      case 'set_lighting':
        return this.handleSetLighting(action.params)
      case 'set_terrain':
        return this.handleSetTerrain(action.params)
      default:
        throw new Error(`未知的 action tool: ${(action as { tool: string }).tool}`)
    }
  }

  // ── 私有处理方法 ──

  private async handlePlaceBlock(params: Record<string, unknown>): Promise<void> {
    requireFields(params, ['x', 'y', 'z', 'block_id'])

    await this.builder.placeBlock(
      toNum(params.x, 'x'),
      toNum(params.y, 'y'),
      toNum(params.z, 'z'),
      toStr(params.block_id, 'block_id'),
      params.material != null ? toStr(params.material, 'material') : undefined,
      params.rotation_y != null ? toNum(params.rotation_y, 'rotation_y') : undefined,
    )
  }

  private async handleRemoveBlock(params: Record<string, unknown>): Promise<void> {
    requireFields(params, ['x', 'y', 'z'])

    await this.builder.removeBlock(
      toNum(params.x, 'x'),
      toNum(params.y, 'y'),
      toNum(params.z, 'z'),
    )
  }

  private async handleSetLighting(params: Record<string, unknown>): Promise<void> {
    requireFields(params, ['time_of_day'])

    await this.builder.setLighting(
      toNum(params.time_of_day, 'time_of_day'),
      params.style != null ? toStr(params.style, 'style') : undefined,
      params.ambient_color != null ? toStr(params.ambient_color, 'ambient_color') : undefined,
    )
  }

  private async handleSetTerrain(params: Record<string, unknown>): Promise<void> {
    requireFields(params, ['x_min', 'z_min', 'x_max', 'z_max', 'biome'])

    await this.builder.setTerrain(
      toNum(params.x_min, 'x_min'),
      toNum(params.z_min, 'z_min'),
      toNum(params.x_max, 'x_max'),
      toNum(params.z_max, 'z_max'),
      toStr(params.biome, 'biome'),
    )
  }
}
