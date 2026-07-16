# Agent 可编程 3D 乐高系统 — 技术设计文档

> **版本**：v1.0  
> **日期**：2026-07-15  
> **作者**：小希（推龙视角）  
> **状态**：Draft — 等主人确认后进入实施

---

## 一、愿景

### 1.1 终局形态

> 让 AI Agent 像搭乐高一样构建 3D 世界。

用户说「给宠物换一个赛博朋克风格的房间」，Agent 理解意图 → 生成构建脚本 → Three.js 引擎执行 → 场景呈现。不需要用户懂 3D 建模，不需要手动拖拽，**用自然语言驱动 3D 内容创作**。

### 1.2 核心洞察

**不是让 AI 直接生成 3D 几何体，而是让 AI 生成「生成 3D 的代码」。**

| 方法 | 直接生成（端到端） | 生成代码再执行（本方案） |
|------|-------------------|------------------------|
| 控制性 | 低（黑盒） | 高（代码可编辑） |
| 可复现 | 否 | 是（同一脚本同一结果） |
| 可组合 | 困难 | 容易（脚本可组合） |
| 精确度 | 低（随机） | 高（精确坐标/尺寸） |
| 可调试 | 不可能 | 可以（看脚本就知道哪里错了） |
| 类比 | AI 画图 | AI 写程序 |

> 这就是 3D-GPT（论文）和 PSP（SIGGRAPH Asia 2025）的核心思想。

### 1.3 与现有系统的关系

```
当前：宠物模块 = 加载一个 PMX 模型 + 显示在窗口
未来：宠物模块 = Agent 可编程的 3D 世界 + 宠物在其中生活
```

宠物不只是一个静态模型，它生活在一个 Agent 可以实时改造的世界里。

---

## 二、架构设计

### 2.1 整体架构

```
┌──────────────────────────────────────────────────────┐
│                       用户                            │
│            "给宠物换一个樱花庭院"                       │
└───────────────────────┬──────────────────────────────┘
                        ↓
┌──────────────────────────────────────────────────────┐
│                  Agent（LLM）                          │
│                                                       │
│  ① 意图理解：用户想要什么场景？                        │
│  ② 结构规划：需要哪些模块？怎么布局？                  │
│  ③ 脚本生成：输出结构化构建指令（JSON）                │
│                                                       │
│  输入：自然语言 + 当前场景状态                         │
│  输出：SceneBuildScript（构建脚本）                    │
└───────────────────────┬──────────────────────────────┘
                        ↓
┌──────────────────────────────────────────────────────┐
│              Tool Calling 层（工具调用）                │
│                                                       │
│  Agent 可调用的 3D 构建工具：                          │
│  ┌─────────────────────────────────────────────┐     │
│  │ place_block     — 放置基础积木               │     │
│  │ build_structure — 构建预制结构（房子/桥/塔）  │     │
│  │ place_object    — 放置 3D 对象（家具/植物）   │     │
│  │ place_character — 放置角色（宠物/NPC）        │     │
│  │ set_terrain     — 设置地形（草地/水面/沙地）  │     │
│  │ set_lighting    — 设置光照（昼夜/氛围灯）     │     │
│  │ set_material    — 设置材质（颜色/纹理/透明）  │     │
│  │ build_road      — 建造道路                   │     │
│  │ remove_block    — 移除积木                   │     │
│  │ get_scene_info  — 查询当前场景信息            │     │
│  └─────────────────────────────────────────────┘     │
└───────────────────────┬──────────────────────────────┘
                        ↓
┌──────────────────────────────────────────────────────┐
│              Scene Builder（场景构建器）                │
│                                                       │
│  解析构建脚本 → 调用 Three.js API → 构建 3D 场景      │
│                                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │ 积木系统      │  │ 模型库        │  │ 材质库      │ │
│  │ (Voxel/Block) │  │ (GLB/PMX)    │  │ (PBR/Toon) │ │
│  └──────────────┘  └──────────────┘  └────────────┘ │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │ 地形系统      │  │ 光照系统      │  │ 物理系统    │ │
│  │ (Terrain)     │  │ (Lighting)   │  │ (Physics)  │ │
│  └──────────────┘  └──────────────┘  └────────────┘ │
└───────────────────────┬──────────────────────────────┘
                        ↓
┌──────────────────────────────────────────────────────┐
│              Three.js 渲染引擎                         │
│                                                       │
│  InstancedMesh 批量渲染 | 后处理管线 | 物理引擎        │
└──────────────────────────────────────────────────────┘
```

### 2.2 数据流

```
用户输入 → Agent(LLM) → SceneBuildScript(JSON) → SceneBuilder → Three.js → 3D 场景
                                ↑
                        场景状态反馈（可选）
                                |
                    Agent 可以查询当前场景状态
                    再决定下一步构建操作
```

### 2.3 核心设计原则

| 原则 | 说明 |
|------|------|
| **脚本驱动** | Agent 输出 JSON 构建脚本，不直接操作 Three.js |
| **幂等性** | 同一脚本执行多次，结果相同 |
| **可组合** | 小脚本可以组合成大脚本 |
| **可回滚** | 每个操作可撤销 |
| **渐进式** | 可以在现有场景上增量修改 |
| **确定性** | 同一坐标同一类型，结果固定（不随机） |

---

## 三、积木系统（Block System）

### 3.1 积木类型定义

```typescript
// 基础积木
interface BlockType {
  id: string                    // 唯一标识
  name: string                  // 显示名称
  category: 'structure' | 'decoration' | 'nature' | 'furniture' | 'light' | 'road'
  geometry: GeometryConfig      // 几何体配置
  defaultMaterial: string       // 默认材质
  size: [number, number, number] // 占用空间 [宽, 高, 深]
  tags: string[]                // 标签（用于 Agent 搜索）
}

// 几何体配置
type GeometryConfig =
  | { type: 'box'; args: [number, number, number] }
  | { type: 'cylinder'; args: [number, number, number, number] }
  | { type: 'sphere'; args: [number, number, number] }
  | { type: 'cone'; args: [number, number, number] }
  | { type: 'model'; path: string }  // 外部 GLB/PMX 模型
  | { type: 'procedural'; generator: string }  // 程序化生成
```

### 3.2 积木库（初始版本）

#### 结构类（Structure）

| ID | 名称 | 几何体 | 尺寸 | 用途 |
|----|------|--------|------|------|
| `cube` | 方块 | Box(1,1,1) | 1×1×1 | 基础积木 |
| `wall` | 墙壁 | Box(1,3,0.2) | 1×3×0.2 | 墙体 |
| `floor` | 地板 | Box(1,0.1,1) | 1×0.1×1 | 地面 |
| `roof_slope` | 斜屋顶 | Cone(0.7,1,4) | 1.4×1×1.4 | 屋顶 |
| `roof_flat` | 平屋顶 | Box(1,0.1,1) | 1×0.1×1 | 平屋顶 |
| `pillar` | 柱子 | Cylinder(0.15,0.15,3) | 0.3×3×0.3 | 支撑柱 |
| `stairs` | 楼梯 | Box(1,0.25,0.5) | 1×0.25×0.5 | 台阶 |
| `window` | 窗户 | Box(0.8,1,0.05) | 0.8×1×0.05 | 透明窗 |

#### 装饰类（Decoration）

| ID | 名称 | 几何体 | 用途 |
|----|------|--------|------|
| `tree_trunk` | 树干 | Cylinder(0.1,0.1,2) | 树干 |
| `tree_canopy` | 树冠 | Sphere(0.8) | 树叶 |
| `bush` | 灌木 | Sphere(0.4) | 绿植 |
| `flower` | 花朵 | Cylinder(0.05,0.15,0.3) | 装饰花 |
| `rock` | 石头 | Sphere(0.3) + 噪波 | 自然石块 |
| `fence` | 栅栏 | Box(1,0.8,0.05) | 围栏 |
| `lamp_post` | 路灯 | Cylinder(0.03,0.03,3) | 街灯 |

#### 家具类（Furniture）

| ID | 名称 | 来源 | 用途 |
|----|------|------|------|
| `chair` | 椅子 | GLB 模型 | 坐具 |
| `table` | 桌子 | GLB 模型 | 台面 |
| `bed` | 床 | GLB 模型 | 睡眠 |
| `bookshelf` | 书架 | GLB 模型 | 存储 |
| `sofa` | 沙发 | GLB 模型 | 座椅 |
| `desk` | 书桌 | GLB 模型 | 工作 |

#### 自然类（Nature）

| ID | 名称 | 几何体 | 用途 |
|----|------|--------|------|
| `water` | 水面 | Plane + 水 Shader | 水池/湖 |
| `grass` | 草地 | Plane + 草纹理 | 地面 |
| `sand` | 沙地 | Plane + 沙纹理 | 沙滩 |
| `snow` | 雪地 | Plane + 雪纹理 | 冬季 |

### 3.3 材质库

```typescript
const MATERIALS = {
  // 建筑材质
  brick:   { color: 0xb35a3f, roughness: 0.8, name: '砖墙' },
  concrete:{ color: 0x999999, roughness: 0.9, name: '混凝土' },
  wood:    { color: 0x8B4513, roughness: 0.6, name: '木材' },
  metal:   { color: 0xcccccc, metalness: 0.9, roughness: 0.2, name: '金属' },
  glass:   { color: 0x88ccff, transparent: true, opacity: 0.3, name: '玻璃' },
  
  // 赛博朋克材质
  neon_pink:   { color: 0xff00ff, emissive: 0xff00ff, emissiveIntensity: 2, name: '霓虹粉' },
  neon_blue:   { color: 0x00ffff, emissive: 0x00ffff, emissiveIntensity: 2, name: '霓虹蓝' },
  neon_green:  { color: 0x00ff00, emissive: 0x00ff00, emissiveIntensity: 2, name: '霓虹绿' },
  dark_metal:  { color: 0x333333, metalness: 0.95, roughness: 0.1, name: '暗金属' },
  
  // 自然材质
  grass:   { color: 0x4a7c3f, roughness: 0.9, name: '草地' },
  water:   { color: 0x2277cc, transparent: true, opacity: 0.6, name: '水面' },
  sand:    { color: 0xd4b896, roughness: 0.95, name: '沙地' },
  snow:    { color: 0xeeeeff, roughness: 0.3, name: '雪地' },
}
```

---

## 四、Agent 工具定义（Tool Schema）

### 4.1 工具注册格式（OpenAI Function Calling 兼容）

```json
{
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "place_block",
        "description": "在指定坐标放置一个积木。坐标系：X=右, Y=上, Z=前。单位：米。",
        "parameters": {
          "type": "object",
          "properties": {
            "x": { "type": "number", "description": "X 坐标" },
            "y": { "type": "number", "description": "Y 坐标（高度）" },
            "z": { "type": "number", "description": "Z 坐标" },
            "block_id": {
              "type": "string",
              "enum": ["cube", "wall", "floor", "roof_slope", "pillar", "window", "..."],
              "description": "积木类型 ID"
            },
            "material": {
              "type": "string",
              "enum": ["brick", "concrete", "wood", "metal", "glass", "neon_pink", "..."],
              "description": "材质 ID"
            },
            "rotation_y": {
              "type": "number",
              "enum": [0, 90, 180, 270],
              "description": "Y 轴旋转角度"
            }
          },
          "required": ["x", "y", "z", "block_id"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "build_structure",
        "description": "在指定位置构建预制结构（房子/桥/塔等）。自动处理墙体、屋顶、门窗。",
        "parameters": {
          "type": "object",
          "properties": {
            "x": { "type": "number" },
            "z": { "type": "number" },
            "type": {
              "type": "string",
              "enum": ["house_small", "house_medium", "tower", "bridge", "wall_segment", "gate"],
              "description": "结构类型"
            },
            "style": {
              "type": "string",
              "enum": ["modern", "classic", "cyberpunk", "japanese", "medieval", "cottage"],
              "description": "建筑风格"
            },
            "width": { "type": "number", "description": "宽度（米）" },
            "depth": { "type": "number", "description": "深度（米）" },
            "height": { "type": "number", "description": "高度（米）" }
          },
          "required": ["x", "z", "type", "style"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "place_object",
        "description": "在指定位置放置 3D 对象（家具/植物/装饰物）。",
        "parameters": {
          "type": "object",
          "properties": {
            "x": { "type": "number" },
            "y": { "type": "number" },
            "z": { "type": "number" },
            "object_id": {
              "type": "string",
              "enum": ["chair", "table", "bed", "bookshelf", "tree_trunk", "tree_canopy", "bush", "flower", "rock", "fence", "lamp_post", "..."],
              "description": "对象 ID"
            },
            "material": { "type": "string" },
            "rotation_y": { "type": "number" },
            "scale": { "type": "number", "description": "缩放比例，默认 1" }
          },
          "required": ["x", "y", "z", "object_id"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "place_character",
        "description": "在指定位置放置角色（宠物/NPC），可指定动画。",
        "parameters": {
          "type": "object",
          "properties": {
            "x": { "type": "number" },
            "z": { "type": "number" },
            "model_path": { "type": "string", "description": "PMX/VRM/GLB 模型路径" },
            "animation": {
              "type": "string",
              "enum": ["idle", "walk", "sit", "wave", "dance", "sleep"],
              "description": "初始动画"
            },
            "facing": { "type": "number", "description": "朝向角度" }
          },
          "required": ["x", "z", "model_path"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "set_terrain",
        "description": "设置指定区域的地形类型。",
        "parameters": {
          "type": "object",
          "properties": {
            "x_min": { "type": "number" },
            "z_min": { "type": "number" },
            "x_max": { "type": "number" },
            "z_max": { "type": "number" },
            "biome": {
              "type": "string",
              "enum": ["grass", "sand", "water", "snow", "stone", "dirt"],
              "description": "地形类型"
            }
          },
          "required": ["x_min", "z_min", "x_max", "z_max", "biome"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "set_lighting",
        "description": "设置场景光照和氛围。",
        "parameters": {
          "type": "object",
          "properties": {
            "time_of_day": {
              "type": "number",
              "description": "时间（0-24），0=午夜, 6=日出, 12=正午, 18=日落"
            },
            "style": {
              "type": "string",
              "enum": ["day", "night", "sunset", "sunrise", "neon", "warm", "cool"],
              "description": "光照风格"
            },
            "ambient_color": { "type": "string", "description": "环境光颜色（hex）" },
            "fog": { "type": "boolean", "description": "是否启用雾效" }
          },
          "required": ["time_of_day"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "build_road",
        "description": "在两点之间建造道路。",
        "parameters": {
          "type": "object",
          "properties": {
            "points": {
              "type": "array",
              "items": {
                "type": "object",
                "properties": {
                  "x": { "type": "number" },
                  "z": { "type": "number" }
                }
              },
              "description": "道路路径点（至少 2 个）"
            },
            "width": { "type": "number", "description": "道路宽度，默认 2" },
            "style": {
              "type": "string",
              "enum": ["asphalt", "cobblestone", "dirt", "neon"],
              "description": "道路材质"
            }
          },
          "required": ["points"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "remove_block",
        "description": "移除指定坐标的积木。",
        "parameters": {
          "type": "object",
          "properties": {
            "x": { "type": "number" },
            "y": { "type": "number" },
            "z": { "type": "number" }
          },
          "required": ["x", "y", "z"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "get_scene_info",
        "description": "查询当前场景信息（积木数量、区域占用、可用空间等）。",
        "parameters": {
          "type": "object",
          "properties": {
            "query": {
              "type": "string",
              "enum": ["bounds", "block_count", "free_space", "objects_at", "terrain_at"],
              "description": "查询类型"
            },
            "x": { "type": "number" },
            "z": { "type": "number" }
          },
          "required": ["query"]
        }
      }
    }
  ]
}
```

---

## 五、构建脚本格式（SceneBuildScript）

### 5.1 脚本结构

```json
{
  "version": "1.0",
  "name": "cherry_blossom_garden",
  "description": "樱花庭院场景",
  "actions": [
    {
      "tool": "set_terrain",
      "params": { "x_min": -10, "z_min": -10, "x_max": 10, "z_max": 10, "biome": "grass" }
    },
    {
      "tool": "set_lighting",
      "params": { "time_of_day": 17, "style": "sunset" }
    },
    {
      "tool": "build_structure",
      "params": { "x": 0, "z": -5, "type": "house_small", "style": "japanese", "width": 6, "depth": 4, "height": 4 }
    },
    {
      "tool": "build_road",
      "params": { "points": [{"x":0,"z":0},{"x":0,"z":-5}], "width": 1.5, "style": "cobblestone" }
    },
    {
      "tool": "place_object",
      "params": { "x": -3, "y": 0, "z": 2, "object_id": "tree_trunk" }
    },
    {
      "tool": "place_object",
      "params": { "x": -3, "y": 2, "z": 2, "object_id": "tree_canopy", "material": "neon_pink" }
    },
    {
      "tool": "place_object",
      "params": { "x": 3, "y": 0, "z": 2, "object_id": "tree_trunk" }
    },
    {
      "tool": "place_object",
      "params": { "x": 3, "y": 2, "z": 2, "object_id": "tree_canopy", "material": "neon_pink" }
    },
    {
      "tool": "place_character",
      "params": { "x": 0, "z": 0, "model_path": "models/pet/default.pmx", "animation": "idle" }
    }
  ]
}
```

### 5.2 脚本执行引擎

```typescript
class SceneBuilder {
  private scene: THREE.Scene
  private blockRegistry: Map<string, BlockType>
  private placedBlocks: Map<string, PlacedBlock>  // "x,y,z" → block

  /** 执行构建脚本 */
  async execute(script: SceneBuildScript): Promise<void> {
    for (const action of script.actions) {
      await this.executeAction(action)
    }
  }

  /** 执行单个动作 */
  private async executeAction(action: SceneAction): Promise<void> {
    switch (action.tool) {
      case 'place_block':
        return this.placeBlock(action.params)
      case 'build_structure':
        return this.buildStructure(action.params)
      case 'place_object':
        return this.placeObject(action.params)
      case 'place_character':
        return this.placeCharacter(action.params)
      case 'set_terrain':
        return this.setTerrain(action.params)
      case 'set_lighting':
        return this.setLighting(action.params)
      case 'build_road':
        return this.buildRoad(action.params)
      case 'remove_block':
        return this.removeBlock(action.params)
    }
  }

  /** 放置积木（核心方法） */
  private placeBlock(params: PlaceBlockParams): void {
    const key = `${params.x},${params.y},${params.z}`
    
    // 如果该位置已有积木，先移除
    if (this.placedBlocks.has(key)) {
      this.removeBlock({ x: params.x, y: params.y, z: params.z })
    }

    const blockType = this.blockRegistry.get(params.block_id)
    if (!blockType) throw new Error(`Unknown block: ${params.block_id}`)

    // 创建几何体
    const geometry = this.createGeometry(blockType.geometry)
    
    // 应用材质
    const material = this.createMaterial(params.material ?? blockType.defaultMaterial)
    
    // 创建网格
    const mesh = new THREE.Mesh(geometry, material)
    mesh.position.set(params.x, params.y, params.z)
    
    if (params.rotation_y) {
      mesh.rotation.y = (params.rotation_y * Math.PI) / 180
    }

    // 用 InstancedMesh 优化批量同类型积木
    this.scene.add(mesh)
    this.placedBlocks.set(key, { mesh, blockType, params })
  }
}
```

---

## 六、与宠物模块的集成

### 6.1 宠物在世界中的行为

```typescript
// 宠物与场景的交互
interface PetWorldInteraction {
  /** 宠物在场景中的位置 */
  position: { x: number; y: number; z: number }
  /** 宠物当前动画 */
  animation: 'idle' | 'walk' | 'sit' | 'sleep'
  /** 宠物看向的目标 */
  lookAt: { x: number; y: number; z: number } | null
  /** 宠物与场景对象的交互 */
  interactWith: string | null  // 积木 ID 或对象 ID
}
```

### 6.2 Agent 构建场景的完整流程

```
用户: "给宠物换一个樱花庭院"
  ↓
Agent 调用 get_scene_info → 了解当前场景
  ↓
Agent 生成构建脚本（JSON）
  ↓
SceneBuilder 执行脚本 → 清除旧场景 → 构建新场景
  ↓
宠物被放置到新场景中
  ↓
用户看到宠物在樱花庭院里
```

### 6.3 后端 API 设计

```
POST /api/v1/pet/scene/build
  Body: { "script": SceneBuildScript }
  → 执行构建脚本，返回执行结果

GET /api/v1/pet/scene/info
  → 返回当前场景信息（积木数量、区域、宠物位置）

POST /api/v1/pet/scene/reset
  → 重置场景到默认状态

POST /api/v1/pet/scene/generate
  Body: { "prompt": "赛博朋克风格的小城镇" }
  → Agent 生成构建脚本 + 执行
```

---

## 七、性能优化策略

### 7.1 InstancedMesh 批量渲染

同类型积木用 `InstancedMesh` 合并 draw call：

```typescript
// 1000 个 brick 方块 → 1 次 draw call（而非 1000 次）
const brickInstances = new THREE.InstancedMesh(
  boxGeometry,
  brickMaterial,
  1000  // 最大实例数
)
```

### 7.2 场景分区（Spatial Partitioning）

```
场景空间 → 16×16 区块（Chunk）
  ↓
只渲染相机附近的区块（类似 Minecraft）
  ↓
远处区块降级为 LOD 或直接不渲染
```

### 7.3 几何体合并（Geometry Merging）

静态积木合并为单个 `BufferGeometry`：

```typescript
// 合并所有不移动的积木为一个几何体
const mergedGeometry = BufferGeometryUtils.mergeGeometries(
  staticBlocks.map(b => b.geometry)
)
```

---

## 八、实施路线

### Phase 1：积木系统基础（1-2 周）

- [ ] 定义积木类型注册表（BlockType Registry）
- [ ] 实现 `placeBlock` / `removeBlock` 核心方法
- [ ] 积木库：cube / wall / floor / roof / pillar
- [ ] 材质库：brick / wood / metal / glass
- [ ] 基础 SceneBuilder 引擎

**验证**：手动调用 API 放置积木，能构建一个简单房子

### Phase 2：Agent 工具注册（1 周）

- [ ] 将 SceneBuilder 方法注册为 Agent 工具（Tool Calling）
- [ ] 实现 `build_structure` / `place_object` 等高级工具
- [ ] Agent 能通过自然语言生成构建脚本
- [ ] 后端 API：`POST /pet/scene/build`

**验证**：用户说「建一个木屋」，Agent 自动生成脚本并构建

### Phase 3：场景系统完善（2 周）

- [ ] 地形系统（set_terrain）
- [ ] 光照系统（set_lighting + 昼夜循环）
- [ ] 道路系统（build_road）
- [ ] 预制建筑模板（house_small / tower / bridge 等）
- [ ] 风格系统（modern / classic / cyberpunk / japanese）

**验证**：Agent 能生成完整的城镇场景

### Phase 4：宠物集成（1 周）

- [ ] 宠物在场景中的放置和移动
- [ ] 宠物与场景对象的交互
- [ ] 宠物动画与场景联动
- [ ] 场景切换（旧场景→新场景）

**验证**：宠物在 Agent 生成的场景中生活

### Phase 5：高级特性（长期）

- [ ] InstancedMesh 批量渲染优化
- [ ] 场景分区 + LOD
- [ ] 场景保存/加载（JSON 序列化）
- [ ] 场景分享（用户之间共享构建脚本）
- [ ] 多宠物支持
- [ ] 物理引擎集成（积木碰撞/重力）

---

## 九、技术参考

| 项目/论文 | 来源 | 核心价值 |
|----------|------|---------|
| 3D-GPT | 论文 | LLM 生成程序化建模脚本的框架 |
| PSP | SIGGRAPH Asia 2025 | 程序化场景描述语言（PSDL） |
| SceneGenAgent | 论文 | Agent + PCG 结合 |
| lo-th/3d.city | GitHub | Three.js 城市建造游戏 |
| tiveor/city-simulator | GitHub | React Three Fiber 城市模拟器 |
| qonqulab/voxelcraft | GitHub | 网页版 Minecraft 体素引擎 |
| Three.js 官方 | 文档 | InstancedMesh / BufferGeometryUtils / WebGPU |
| micropolisJS | GitHub | SimCity 开源城市仿真引擎 |

---

## 十、风险与约束

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| Agent 生成的脚本质量不稳定 | 场景可能不美观 | 提供预制模板 + 约束规则 |
| 积木种类不够丰富 | 场景单调 | 渐进扩充积木库 + 支持外部模型 |
| 性能瓶颈（大量积木） | 渲染卡顿 | InstancedMesh + 场景分区 + LOD |
| 场景序列化体积大 | 保存/加载慢 | 只序列化增量操作（脚本而非快照） |
| Agent 工具调用延迟 | 用户等待时间长 | 流式生成 + 渐进渲染 |

---

> **下一步**：主人确认方向后，从 Phase 1 开始实施。
