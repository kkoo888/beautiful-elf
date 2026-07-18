/**
 * Scene Tools — Agent 工具注册
 *
 * 对应文档：agent-3d-building-block-system.md §4.1
 * 将 SceneBuilder 方法注册为 Agent 可调用的工具（OpenAI Function Calling 兼容）。
 */
import type { SceneBuilder } from './scene-builder'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** JSON Schema 参数定义 */
export interface ToolParameter {
  type: string
  description?: string
  enum?: string[]
  items?: ToolParameter
  properties?: Record<string, ToolParameter>
  required?: string[]
  default?: unknown
}

/** Agent 可调用的工具定义 */
export interface SceneTool {
  name: string
  description: string
  parameters: {
    type: 'object'
    properties: Record<string, ToolParameter>
    required: string[]
  }
  execute: (params: Record<string, unknown>, builder: SceneBuilder) => unknown
}

// ---------------------------------------------------------------------------
// Tool Registry
// ---------------------------------------------------------------------------

export class SceneToolRegistry {
  private tools: Map<string, SceneTool> = new Map()

  /** 注册一个工具 */
  registerTool(tool: SceneTool): void {
    this.tools.set(tool.name, tool)
  }

  /** 按名称获取工具 */
  getTool(name: string): SceneTool | undefined {
    return this.tools.get(name)
  }

  /** 列出所有工具的 schema（用于 Agent prompt） */
  listTools(): Array<{ name: string; description: string; parameters: SceneTool['parameters'] }> {
    return [...this.tools.values()].map(t => ({
      name: t.name,
      description: t.description,
      parameters: t.parameters,
    }))
  }

  /** 执行工具 */
  executeTool(name: string, params: Record<string, unknown>, builder: SceneBuilder): unknown {
    const tool = this.tools.get(name)
    if (!tool) throw new Error(`Unknown tool: ${name}`)
    return tool.execute(params, builder)
  }
}

// ---------------------------------------------------------------------------
// Built-in Tools
// ---------------------------------------------------------------------------

const placeBlockTool: SceneTool = {
  name: 'place_block',
  description: '在指定坐标放置一个积木。坐标系：X=右, Y=上, Z=前。单位：米。',
  parameters: {
    type: 'object',
    properties: {
      x: { type: 'number', description: 'X 坐标' },
      y: { type: 'number', description: 'Y 坐标（高度）' },
      z: { type: 'number', description: 'Z 坐标' },
      block_id: {
        type: 'string',
        description: '积木类型 ID',
        enum: ['cube', 'wall', 'floor', 'roof_slope', 'roof_flat', 'pillar', 'stairs', 'window',
          'tree_trunk', 'tree_canopy', 'bush', 'flower', 'rock', 'fence', 'lamp_post',
          'chair', 'table', 'bed', 'bookshelf', 'sofa', 'desk',
          'water', 'grass', 'sand', 'snow'],
      },
      material: {
        type: 'string',
        description: '材质 ID（可选，默认使用积木的默认材质）',
        enum: ['brick', 'concrete', 'wood', 'metal', 'glass',
          'neon_pink', 'neon_blue', 'neon_green', 'dark_metal',
          'grass', 'water', 'sand', 'snow'],
      },
      rotation_y: {
        type: 'number',
        description: 'Y 轴旋转角度（0/90/180/270）',
      },
    },
    required: ['x', 'y', 'z', 'block_id'],
  },
  execute(params: Record<string, unknown>, builder: SceneBuilder) {
    builder.placeBlock(
      params.block_id as string,
      params.x as number,
      params.y as number,
      params.z as number,
      (params.rotation_y as number) ?? 0,
      params.material as string | undefined,
    )
    return { success: true, position: { x: params.x, y: params.y, z: params.z } }
  },
}

const buildStructureTool: SceneTool = {
  name: 'build_structure',
  description: '在指定位置构建预制结构（房子/桥/塔等）。自动处理墙体、屋顶、门窗。',
  parameters: {
    type: 'object',
    properties: {
      x: { type: 'number', description: '起始 X 坐标' },
      z: { type: 'number', description: '起始 Z 坐标' },
      type: {
        type: 'string',
        enum: ['house_small', 'house_medium', 'tower', 'bridge', 'wall_segment', 'gate'],
        description: '结构类型',
      },
      style: {
        type: 'string',
        enum: ['modern', 'classic', 'cyberpunk', 'japanese', 'medieval', 'cottage'],
        description: '建筑风格',
      },
      width: { type: 'number', description: '宽度（米），默认 4' },
      depth: { type: 'number', description: '深度（米），默认 4' },
      height: { type: 'number', description: '高度（米），默认 3' },
    },
    required: ['x', 'z', 'type', 'style'],
  },
  execute(params: Record<string, unknown>, builder: SceneBuilder) {
    const x = params.x as number
    const z = params.z as number
    const w = (params.width as number) ?? 4
    const d = (params.depth as number) ?? 4
    const h = (params.height as number) ?? 3
    const style = params.style as string

    // 选择材质
    const wallMat = style === 'cyberpunk' ? 'dark_metal' : style === 'japanese' ? 'wood' : 'brick'
    const roofMat = style === 'cyberpunk' ? 'neon_blue' : 'brick'
    const floorMat = style === 'cyberpunk' ? 'dark_metal' : 'wood'

    // 地板
    for (let dx = 0; dx < w; dx++) {
      for (let dz = 0; dz < d; dz++) {
        builder.placeBlock('floor', x + dx, 0, z + dz, 0, floorMat)
      }
    }

    // 墙壁
    const wallH = Math.ceil(h / 3)
    for (let dy = 0; dy < wallH; dy++) {
      for (let dx = 0; dx < w; dx++) {
        builder.placeBlock('wall', x + dx, dy * 3, z, 0, wallMat)
        builder.placeBlock('wall', x + dx, dy * 3, z + d - 1, 0, wallMat)
      }
      for (let dz = 1; dz < d - 1; dz++) {
        builder.placeBlock('wall', x, dy * 3, z + dz, 0, wallMat)
        builder.placeBlock('wall', x + w - 1, dy * 3, z + dz, 0, wallMat)
      }
    }

    // 屋顶
    for (let dx = 0; dx < w; dx++) {
      for (let dz = 0; dz < d; dz++) {
        builder.placeBlock('roof_flat', x + dx, h, z + dz, 0, roofMat)
      }
    }

    return { success: true, bounds: { x, z, width: w, depth: d, height: h } }
  },
}

const placeObjectTool: SceneTool = {
  name: 'place_object',
  description: '在指定位置放置 3D 对象（家具/植物/装饰物）。',
  parameters: {
    type: 'object',
    properties: {
      x: { type: 'number', description: 'X 坐标' },
      y: { type: 'number', description: 'Y 坐标' },
      z: { type: 'number', description: 'Z 坐标' },
      object_id: {
        type: 'string',
        description: '对象 ID',
        enum: ['chair', 'table', 'bed', 'bookshelf', 'sofa', 'desk',
          'tree_trunk', 'tree_canopy', 'bush', 'flower', 'rock', 'fence', 'lamp_post'],
      },
      material: { type: 'string', description: '材质 ID（可选）' },
      rotation_y: { type: 'number', description: 'Y 轴旋转角度' },
      scale: { type: 'number', description: '缩放比例，默认 1' },
    },
    required: ['x', 'y', 'z', 'object_id'],
  },
  execute(params: Record<string, unknown>, builder: SceneBuilder) {
    builder.placeBlock(
      params.object_id as string,
      params.x as number,
      params.y as number,
      params.z as number,
      (params.rotation_y as number) ?? 0,
      params.material as string | undefined,
    )
    return { success: true, object: params.object_id, position: { x: params.x, y: params.y, z: params.z } }
  },
}

const placeCharacterTool: SceneTool = {
  name: 'place_character',
  description: '在指定位置放置角色（宠物/NPC），可指定动画。',
  parameters: {
    type: 'object',
    properties: {
      x: { type: 'number', description: 'X 坐标' },
      z: { type: 'number', description: 'Z 坐标' },
      model_path: { type: 'string', description: 'PMX/VRM/GLB 模型路径' },
      animation: {
        type: 'string',
        enum: ['idle', 'walk', 'sit', 'wave', 'dance', 'sleep'],
        description: '初始动画',
      },
      facing: { type: 'number', description: '朝向角度' },
    },
    required: ['x', 'z', 'model_path'],
  },
  execute(params: Record<string, unknown>, _builder: SceneBuilder) {
    // 角色放置需要模型加载，这里返回指令供前端执行
    return {
      success: true,
      action: 'place_character',
      x: params.x,
      z: params.z,
      model_path: params.model_path,
      animation: params.animation ?? 'idle',
      facing: params.facing ?? 0,
    }
  },
}

const setTerrainTool: SceneTool = {
  name: 'set_terrain',
  description: '设置指定区域的地形类型。',
  parameters: {
    type: 'object',
    properties: {
      x_min: { type: 'number', description: 'X 最小值' },
      z_min: { type: 'number', description: 'Z 最小值' },
      x_max: { type: 'number', description: 'X 最大值' },
      z_max: { type: 'number', description: 'Z 最大值' },
      biome: {
        type: 'string',
        enum: ['grass', 'sand', 'water', 'snow', 'stone', 'dirt'],
        description: '地形类型',
      },
    },
    required: ['x_min', 'z_min', 'x_max', 'z_max', 'biome'],
  },
  execute(params: Record<string, unknown>, builder: SceneBuilder) {
    const biome = params.biome as string
    const materialMap: Record<string, string> = {
      grass: 'grass', sand: 'sand', water: 'water',
      snow: 'snow', stone: 'concrete', dirt: 'sand',
    }
    const matId = materialMap[biome] ?? 'grass'

    for (let x = params.x_min as number; x <= (params.x_max as number); x++) {
      for (let z = params.z_min as number; z <= (params.z_max as number); z++) {
        builder.placeBlock(biome === 'water' ? 'water' : 'grass', x, 0, z, 0, matId)
      }
    }
    return { success: true, area: { x_min: params.x_min, z_min: params.z_min, x_max: params.x_max, z_max: params.z_max }, biome }
  },
}

const setLightingTool: SceneTool = {
  name: 'set_lighting',
  description: '设置场景光照和氛围。',
  parameters: {
    type: 'object',
    properties: {
      time_of_day: { type: 'number', description: '时间（0-24），0=午夜, 6=日出, 12=正午, 18=日落' },
      style: {
        type: 'string',
        enum: ['day', 'night', 'sunset', 'sunrise', 'neon', 'warm', 'cool'],
        description: '光照风格',
      },
      ambient_color: { type: 'string', description: '环境光颜色（hex）' },
      fog: { type: 'boolean', description: '是否启用雾效' },
    },
    required: ['time_of_day'],
  },
  execute(params: Record<string, unknown>, _builder: SceneBuilder) {
    return {
      success: true,
      action: 'set_lighting',
      time_of_day: params.time_of_day,
      style: params.style ?? 'day',
      ambient_color: params.ambient_color,
      fog: params.fog ?? false,
    }
  },
}

const buildRoadTool: SceneTool = {
  name: 'build_road',
  description: '在两点之间建造道路。',
  parameters: {
    type: 'object',
    properties: {
      points: {
        type: 'array',
        description: '道路路径点（至少 2 个）',
        items: {
          type: 'object',
          properties: {
            x: { type: 'number' },
            z: { type: 'number' },
          },
          required: ['x', 'z'],
        },
      },
      width: { type: 'number', description: '道路宽度，默认 2' },
      style: {
        type: 'string',
        enum: ['asphalt', 'cobblestone', 'dirt', 'neon'],
        description: '道路材质',
      },
    },
    required: ['points'],
  },
  execute(params: Record<string, unknown>, builder: SceneBuilder) {
    const points = params.points as Array<{ x: number; z: number }>
    const roadWidth = (params.width as number) ?? 2
    const style = (params.style as string) ?? 'asphalt'
    const matMap: Record<string, string> = {
      asphalt: 'concrete', cobblestone: 'stone', dirt: 'sand', neon: 'neon_blue',
    }
    const matId = matMap[style] ?? 'concrete'

    // 简单直线连接相邻点
    for (let i = 0; i < points.length - 1; i++) {
      const p0 = points[i]
      const p1 = points[i + 1]
      const dx = p1.x - p0.x
      const dz = p1.z - p0.z
      const steps = Math.max(Math.abs(dx), Math.abs(dz))

      for (let s = 0; s <= steps; s++) {
        const t = steps === 0 ? 0 : s / steps
        const rx = Math.round(p0.x + dx * t)
        const rz = Math.round(p0.z + dz * t)

        for (let w = 0; w < roadWidth; w++) {
          builder.placeBlock('floor', rx, 0, rz + w, 0, matId)
        }
      }
    }

    return { success: true, road_length: points.length, style }
  },
}

const removeBlockTool: SceneTool = {
  name: 'remove_block',
  description: '移除指定坐标的积木。',
  parameters: {
    type: 'object',
    properties: {
      x: { type: 'number', description: 'X 坐标' },
      y: { type: 'number', description: 'Y 坐标' },
      z: { type: 'number', description: 'Z 坐标' },
    },
    required: ['x', 'y', 'z'],
  },
  execute(params: Record<string, unknown>, builder: SceneBuilder) {
    builder.removeBlock(params.x as number, params.y as number, params.z as number)
    return { success: true, removed: { x: params.x, y: params.y, z: params.z } }
  },
}

const getSceneInfoTool: SceneTool = {
  name: 'get_scene_info',
  description: '查询当前场景信息（积木数量、区域占用、可用空间等）。',
  parameters: {
    type: 'object',
    properties: {
      query: {
        type: 'string',
        enum: ['bounds', 'block_count', 'free_space', 'objects_at', 'terrain_at'],
        description: '查询类型',
      },
      x: { type: 'number', description: 'X 坐标（objects_at/terrain_at 需要）' },
      z: { type: 'number', description: 'Z 坐标（objects_at/terrain_at 需要）' },
    },
    required: ['query'],
  },
  execute(params: Record<string, unknown>, builder: SceneBuilder) {
    const query = params.query as string

    switch (query) {
      case 'block_count':
        return { query, count: builder.size }

      case 'bounds': {
        let minX = Infinity, maxX = -Infinity, minZ = Infinity, maxZ = -Infinity
        for (const entry of builder.entries()) {
          const key = entry.key
          const [kx, , kz] = key.split(',').map(Number)
          minX = Math.min(minX, kx)
          maxX = Math.max(maxX, kx)
          minZ = Math.min(minZ, kz)
          maxZ = Math.max(maxZ, kz)
        }
        return { query, bounds: { minX, maxX, minZ, maxZ } }
      }

      case 'objects_at': {
        const block = builder.getBlockAt(params.x as number, 0, params.z as number)
        return { query, x: params.x, z: params.z, block: block?.blockType.id ?? null }
      }

      default:
        return { query, error: `Unsupported query: ${query}` }
    }
  },
}

// ---------------------------------------------------------------------------
// Default Registry
// ---------------------------------------------------------------------------

/** 创建包含所有内置工具的默认注册表 */
export function createDefaultToolRegistry(): SceneToolRegistry {
  const registry = new SceneToolRegistry()

  registry.registerTool(placeBlockTool)
  registry.registerTool(buildStructureTool)
  registry.registerTool(placeObjectTool)
  registry.registerTool(placeCharacterTool)
  registry.registerTool(setTerrainTool)
  registry.registerTool(setLightingTool)
  registry.registerTool(buildRoadTool)
  registry.registerTool(removeBlockTool)
  registry.registerTool(getSceneInfoTool)

  return registry
}
