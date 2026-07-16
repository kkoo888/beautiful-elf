# Agent 可编程 3D 乐高系统 — 技术设计文档

> **版本**：v2.0  
> **日期**：2026-07-16  
> **作者**：小希（推龙+管龙视角）  
> **状态**：Ready — 可断点续开发

---

## 零、开发任务清单（可断点续开发）

> 每个任务独立可验收，中断后从任意任务继续。
> 完成一个任务 → 打 ✅ → 提交 → 下一个。

### 任务依赖图

```
T1 积木类型定义
  ↓
T2 场景构建器（SceneBuilder）
  ↓
T3 Agent 工具注册 → T4 构建脚本执行引擎
  ↓                       ↓
T5 后端 API            T5 后端 API
  ↓
T6 动画系统 → T7 骨骼映射 → T8 视频动捕
  ↓
T9 前端集成 → T10 测试验收
```

### T1：积木类型定义 + 材质库

| 项目 | 内容 |
|------|------|
| **描述** | 定义积木类型注册表 + 材质库 + 光源配置 |
| **依赖** | 无（第一个任务） |
| **预计** | 1 天 |
| **输入** | §3.1 积木类型定义 + §3.2 积木库 + §3.3 材质库 |
| **输出** | `src/lib/block-registry.ts` + `src/lib/materials.ts` |
| **验收** | 能通过 ID 查到积木类型和材质配置 |

### T2：场景构建器（SceneBuilder）

| 项目 | 内容 |
|------|------|
| **描述** | 实现 `placeBlock` / `removeBlock` / `buildStructure` 核心方法 |
| **依赖** | T1 |
| **预计** | 2 天 |
| **输入** | §5.2 脚本执行引擎 + §3.4 Three.js 基础方块 |
| **输出** | `src/lib/scene-builder.ts` |
| **验收** | 手动调用 API 能放置积木构建简单房子 |

### T3：Agent 工具注册

| 项目 | 内容 |
|------|------|
| **描述** | 将 SceneBuilder 方法注册为 Agent 可调用的工具 |
| **依赖** | T2 |
| **预计** | 1 天 |
| **输入** | §4.1 工具注册格式 + §3.14 动画工具 Schema |
| **输出** | `backend/app/services/scene_tool_service.py` |
| **验收** | Agent 能通过 Tool Calling 调用 place_block / build_structure |

### T4：构建脚本执行引擎

| 项目 | 内容 |
|------|------|
| **描述** | 解析 JSON 构建脚本，批量执行构建动作 |
| **依赖** | T2 |
| **预计** | 1 天 |
| **输入** | §5.1 脚本结构 + §5.2 执行引擎 |
| **输出** | `src/lib/script-executor.ts` |
| **验收** | 输入 JSON 脚本 → 输出完整 3D 场景 |

### T5：后端 API + 数据库

| 项目 | 内容 |
|------|------|
| **描述** | 场景 CRUD API + 动画管理 API + 数据库建表 |
| **依赖** | T3, T4 |
| **预计** | 1 天 |
| **输入** | §6.3 后端 API 设计 + §3.8 数据库设计 |
| **输出** | `backend/app/api/v1/scene.py` + `backend/app/models/animation.py` |
| **验收** | curl 能调用场景构建 API + 动画 CRUD API |

### T6：动画系统（AnimationMixer + 状态机）

| 项目 | 内容 |
|------|------|
| **描述** | 实现动画加载、播放、状态机、混合过渡 |
| **依赖** | T2 |
| **预计** | 2 天 |
| **输入** | §3.7 骨骼动画标准 + §3.9 状态机实现 |
| **输出** | `src/lib/animation-manager.ts` + `src/lib/animation-state-machine.ts` |
| **验收** | 能加载 Mixamo FBX 动画并在 PMX 模型上播放 |

### T7：骨骼映射 + 重定向

| 项目 | 内容 |
|------|------|
| **描述** | 实现 Mixamo↔PMX 骨骼映射 + 动画重定向 |
| **依赖** | T6 |
| **预计** | 1 天 |
| **输入** | §3.11 骨骼映射表 + §3.13 PMX 接入方案 |
| **输出** | `src/lib/bone-retargeter.ts` |
| **验收** | Mixamo 动画能正确套用到 PMX 模型 |

### T8：视频动捕管线

| 项目 | 内容 |
|------|------|
| **描述** | MediaPipe→3D 坐标→动画 JSON→Three.js 播放 |
| **依赖** | T6, T7 |
| **预计** | 3 天 |
| **输入** | §3.10 视频动捕管线 + §3.12 参考项目 |
| **输出** | `backend/services/motion-capture.py` + `src/lib/animation-loader.ts` |
| **验收** | 上传舞蹈视频 → 宠物播放对应动画 |

### T9：前端集成 + UI

| 项目 | 内容 |
|------|------|
| **描述** | 将场景系统集成到宠物窗口，添加动画控制 UI |
| **依赖** | T5, T6 |
| **预计** | 2 天 |
| **输入** | §6 宠物模块集成 |
| **输出** | 修改 `pet-scene.ts` + 新增动画控制面板 |
| **验收** | 宠物在 Agent 生成的场景中播放动画 |

### T10：测试验收

| 项目 | 内容 |
|------|------|
| **描述** | 端到端测试：Agent 生成场景 + 宠物动画 + 截图 |
| **依赖** | T9 |
| **预计** | 1 天 |
| **输入** | 所有前置任务 |
| **输出** | 测试报告 + 截图 |
| **验收** | 用户说「给宠物换一个赛博朋克房间」→ 场景+动画呈现 |

### 进度追踪

| 任务 | 状态 | 完成日期 | 提交 hash |
|------|------|---------|----------|
| T1 积木类型定义 | ⬜ 未开始 | — | — |
| T2 场景构建器 | ⬜ 未开始 | — | — |
| T3 Agent 工具注册 | ⬜ 未开始 | — | — |
| T4 构建脚本引擎 | ⬜ 未开始 | — | — |
| T5 后端 API | ⬜ 未开始 | — | — |
| T6 动画系统 | ⬜ 未开始 | — | — |
| T7 骨骼映射 | ⬜ 未开始 | — | — |
| T8 视频动捕 | ⬜ 未开始 | — | — |
| T9 前端集成 | ⬜ 未开始 | — | — |
| T10 测试验收 | ⬜ 未开始 | — | — |

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

### 3.4 Three.js 原生基础方块

> 类比 Minecraft：只需 1 种方块就能建造一切。Three.js 也有「最小可用方块集」。

#### 几何体（形状方块）— 14 种

| # | 几何体 | 代码 | 用途 |
|---|--------|------|------|
| 1 | **方块** | `BoxGeometry(w,h,d)` | 墙壁、地板、家具、建筑 |
| 2 | **球体** | `SphereGeometry(r)` | 树冠、灯泡、眼球、行星 |
| 3 | **圆柱** | `CylinderGeometry(rT,rB,h)` | 树干、柱子、路灯、杯子 |
| 4 | **圆锥** | `ConeGeometry(r,h)` | 屋顶、帽子、箭头、树木 |
| 5 | **圆环** | `TorusGeometry(r,tube)` | 甜甜圈、轮胎、光环 |
| 6 | **平面** | `PlaneGeometry(w,h)` | 地面、水面、墙壁、屏幕 |
| 7 | **圆面** | `CircleGeometry(r)` | 圆形地面、光盘、表盘 |
| 8 | **环面** | `RingGeometry(rI,rO)` | 光环、靶子 |
| 9 | **胶囊** | `CapsuleGeometry(r,h)` | 角色身体、药丸 |
| 10 | **圆环结** | `TorusKnotGeometry(p,q)` | 装饰、特效 |
| 11 | **十二面体** | `DodecahedronGeometry(r)` | 宝石、骰子 |
| 12 | **二十面体** | `IcosahedronGeometry(r)` | 地球、低面数球 |
| 13 | **挤压体** | `ExtrudeGeometry(shape,opts)` | 任意 2D→3D |
| 14 | **旋转体** | `LatheGeometry(points)` | 花瓶、酒杯 |

#### 材质（外观方块）— 9 种

| # | 材质 | 代码 | 效果 | 性能 |
|---|------|------|------|------|
| 1 | **基础** | `MeshBasicMaterial` | 无光照，纯色/贴图 | ⚡ 最快 |
| 2 | **朗伯** | `MeshLambertMaterial` | 漫反射，哑光 | ⚡ 快 |
| 3 | **冯氏** | `MeshPhongMaterial` | 高光反射，塑料感 | ⚡ 快 |
| 4 | **标准 PBR** | `MeshStandardMaterial` | 物理真实渲染 | ⚡ 中等 |
| 5 | **物理 PBR** | `MeshPhysicalMaterial` | 玻璃/清漆/次表面散射 | 🐌 较慢 |
| 6 | **卡通** | `MeshToonMaterial` | 动漫/Cel-shading | ⚡ 快 |
| 7 | **法线** | `MeshNormalMaterial` | 法线可视化（调试） | ⚡ 快 |
| 8 | **深度** | `MeshDepthMaterial` | 深度可视化 | ⚡ 快 |
| 9 | **自定义** | `ShaderMaterial` | 完全自定义 shader | 🔧 可控 |

**选择指南**：桌面宠物/卡通→`MeshToonMaterial`，写实→`MeshStandardMaterial`，玻璃/水→`MeshPhysicalMaterial`

#### 光源（光照方块）— 5 种

| # | 光源 | 代码 | 效果 | 阴影 |
|---|------|------|------|------|
| 1 | **环境光** | `AmbientLight` | 全局均匀照明 | ❌ |
| 2 | **平行光** | `DirectionalLight` | 太阳光 | ✅ |
| 3 | **点光源** | `PointLight` | 灯泡 | ✅ |
| 4 | **聚光灯** | `SpotLight` | 手电筒锥形光 | ✅ |
| 5 | **半球光** | `HemisphereLight` | 天空+地面渐变 | ❌ |

**经典组合**：`AmbientLight` + `DirectionalLight` + `HemisphereLight`（宠物场景）

#### 纹理（贴图方块）— 7 种

| # | 纹理 | 代码 | 用途 |
|---|------|------|------|
| 1 | **图片纹理** | `Texture` | 最常用，加载图片 |
| 2 | **Canvas 纹理** | `CanvasTexture` | 动态文字/图案 |
| 3 | **视频纹理** | `VideoTexture` | 视频播放到表面 |
| 4 | **立方体纹理** | `CubeTexture` | 天空盒、环境反射 |
| 5 | **数据纹理** | `DataTexture` | 像素级数据 |
| 6 | **3D 纹理** | `Data3DTexture` | 体积渲染（烟雾/云） |
| 7 | **压缩纹理** | `CompressedTexture` | GPU 压缩格式 |

**PBR 贴图通道**：颜色(map) + 法线(normalMap) + 粗糙度(roughnessMap) + 金属度(metalnessMap) + 环境遮蔽(aoMap) + 自发光(emissiveMap)

#### 动画（运动方块）— 6 种

| # | 动画类型 | 代码 | 用途 |
|---|---------|------|------|
| 1 | **关键帧动画** | `KeyframeTrack` | 位置/旋转/缩放随时间变化 |
| 2 | **动画剪辑** | `AnimationClip` | 一组关键帧的打包 |
| 3 | **动画混合器** | `AnimationMixer` | 播放、混合、过渡多个动画 |
| 4 | **骨骼动画** | `Skeleton` + `Bone` | 角色骨骼驱动 |
| 5 | **变形目标** | `morphTargetInfluences` | 面部表情、口型 |
| 6 | **程序动画** | 代码控制 position/rotation | 待机呼吸、鼠标追踪 |

**动画混合**：`walkAction.crossFadeTo(runAction, 0.3)` — 0.3 秒平滑过渡

#### 后处理（特效方块）— 8 种

| # | 特效 | 代码 | 效果 |
|---|------|------|------|
| 1 | **辉光** | `UnrealBloomPass` | 发光物体泛光 |
| 2 | **描边** | `OutlinePass` | 选中物体轮廓线 |
| 3 | **景深** | `BokehPass` | 背景虚化 |
| 4 | **环境光遮蔽** | `SSAOPass` | 角落阴影增强 |
| 5 | **色调映射** | `ToneMappingPass` | HDR→SDR |
| 6 | **抗锯齿** | `FXAASmoothPass` | 边缘平滑 |
| 7 | **暗角** | `VignetteEffect` | 画面边缘变暗 |
| 8 | **颜色校正** | `LUTPass` | 滤镜风格化 |

#### 物理（力学方块）— 3 种

| # | 物理引擎 | 代码 | 用途 |
|---|---------|------|------|
| 1 | **Ammo.js** | `MMDPhysics` | 布料/头发/刚体 |
| 2 | **cannon-es** | `@react-three/cannon` | 轻量级刚体物理 |
| 3 | **Rapier** | `@react-three/rapier` | 高性能 Rust→WASM |

**简化物理（不用引擎）**：重力 `mesh.position.y -= 9.8 * delta²` + AABB 碰撞 `box1.intersectsBox(box2)`

#### 控制器（交互方块）— 5 种

| # | 控制器 | 代码 | 用途 |
|---|--------|------|------|
| 1 | **轨道控制** | `OrbitControls` | 围绕目标旋转相机 |
| 2 | **第一人称** | `PointerLockControls` | FPS 视角 |
| 3 | **飞行控制** | `FlyControls` | 自由飞行 |
| 4 | **拖拽控制** | `DragControls` | 拖拽物体 |
| 5 | **变换控制** | `TransformControls` | 移动/旋转/缩放手柄 |

### 3.5 最小可用方块集（Minecraft 思维）

> 就像 Minecraft 只需要 1 种方块就能建造一切，Three.js 的「最小可用集」：

```
几何体：Box + Sphere + Cylinder + Plane（4 种覆盖 80%）
材质：  MeshStandardMaterial（PBR 万能）+ MeshToonMaterial（卡通）
光源：  AmbientLight + DirectionalLight（2 种覆盖 80%）
纹理：  Texture（图片贴图）+ CubeTexture（天空盒）
动画：  AnimationMixer + KeyframeTrack（万能动画系统）
物理：  简化重力 + AABB 碰撞（80% 场景够用）
后处理：UnrealBloomPass + OutlinePass（2 种覆盖 80%）
控制：  OrbitControls（调试）+ 程序化控制（运行时）
```

**只要这 12 个方块，就能搭建出完整的 3D 世界、人物、动画和特效。**

### 3.6 乐高物理原理对齐

| 乐高原理 | Three.js 实现 | 说明 |
|---------|--------------|------|
| 8mm 网格 | 1 单位网格 | Three.js 坐标系，position.x 整数 |
| 凸点-管互锁 | 碰撞检测表 grid Map | `grid["x,y,z"] = brickId` |
| 90° 旋转约束 | `rotation.y ∈ {0, π/2, π, 3π/2}` | 只允许 90° 倍数 |
| 支撑约束 | 底面接触检测 | 每个积木必须有支撑 |
| InstancedMesh | 同类积木合并 draw call | 1000 个同类型→1 次渲染 |
| LOD 层次 | 近处完整/远处简化 | 降低远距离渲染开销 |
| 咬合力 | 网格占用表 O(1) 查表 | 比物理碰撞检测快 100x |

**核心洞察**：乐高的「简单」来自于**强约束**——网格对齐、90° 旋转、整层堆叠。这些约束让碰撞检测从 O(n²) 变成 O(1)，让 Agent 生成构建脚本变得可靠（不会有「差 0.1mm 对不上」的问题）。

### 3.7 骨骼动画标准与动画复用

> 核心问题：每个模型需要一套骨骼吗？**不需要。** 有标准骨骼系统可以复用。

#### 三大标准骨骼系统

| 标准 | 骨骼数量 | 自动绑骨 | 动画库 | 格式 | Three.js |
|------|---------|---------|--------|------|----------|
| **Mixamo**（Adobe） | 62 个标准节点 | ✅ 上传即用 | 2000+ 免费 | FBX | FBXLoader |
| **VRM**（VR 联盟） | Humanoid 标准映射 | ✅ | 表色+Spring Bone | glTF 扩展 | @pixiv/three-vrm |
| **SMPL**（学术） | 参数化人体 | — | — | 自定义 | 自定义解析 |

#### Mixamo 标准骨骼（推荐起步）

```
任意 3D 模型 → Mixamo 自动绑骨 → 62 个标准骨骼 → 下载动画 FBX
                                      ↓
                          所有模型共享同一套骨骼标准
                          同一段动画可以套用到任何模型
```

#### VRM 标准骨骼（推荐长期）

VRM 定义了标准 Humanoid 骨骼名称，每个模型内部骨骼名可以不同，但都映射到标准名：

```
标准骨骼：hips, spine, chest, neck, head
          leftUpperArm, leftLowerArm, leftHand
          rightUpperArm, rightLowerArm, rightHand
          leftUpperLeg, leftLowerLeg, leftFoot
          rightUpperLeg, rightLowerLeg, rightFoot
```

**核心价值**：同一段动画可以套用到任何 VRM 模型，不需要每个模型单独做动画。

#### 动画复用三种方式

| 方式 | 适用场景 | 工作量 |
|------|---------|--------|
| 共享骨骼标准 | 所有模型遵循同一标准（如 Mixamo） | 零额外工作 |
| 骨骼重定向 | 自定义骨骼→自定义骨骼，需映射表 | 中等 |
| AI 自动重定向 | MotionBERT 输出→自动映射到任意模型 | 低（依赖 AI） |

### 3.8 动画数据格式规范

> 补充 #1：动画数据存成什么格式？字段定义是什么？

#### 推荐格式：JSON（前端友好）+ BVH（兼容标准工具）

```typescript
// 动画数据 JSON Schema
interface AnimationData {
  name: string              // 动画名称，如 "dance_hiphop"
  duration: number          // 总时长（秒）
  fps: number               // 帧率，通常 30
  boneCount: number         // 骨骼数量
  frames: FrameData[]       // 每帧数据
}

interface FrameData {
  timestamp: number         // 时间戳（秒）
  bones: {
    [boneName: string]: {
      position: [number, number, number]       // XYZ 世界坐标
      rotation: [number, number, number, number] // 四元数 [x, y, z, w]
    }
  }
}
```

#### 存储方式

```
backend/uploads/animations/
  ├── dance_hiphop.json      (舞蹈动画)
  ├── walk_normal.json       (走路动画)
  ├── idle_breathing.json    (待机呼吸)
  └── wave_hello.json        (挥手动画)
```

#### 数据库记录

```sql
CREATE TABLE pet_animation (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(100) NOT NULL COMMENT '动画名称',
  file_path VARCHAR(500) NOT NULL COMMENT 'JSON 文件路径',
  duration DECIMAL(10,2) NOT NULL COMMENT '时长(秒)',
  fps INT NOT NULL DEFAULT 30 COMMENT '帧率',
  bone_count INT NOT NULL COMMENT '骨骼数',
  category VARCHAR(50) NOT NULL DEFAULT 'custom' COMMENT '分类: idle/walk/dance/custom',
  source VARCHAR(50) NOT NULL DEFAULT 'mixamo' COMMENT '来源: mixamo/video/ai',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  is_deleted INT UNSIGNED NOT NULL DEFAULT 0
);
```

### 3.9 动画状态机实现

> 补充 #2：状态机的数据结构和转换规则

#### 状态机数据结构

```typescript
interface AnimationState {
  name: string                    // 状态名: idle, walk, run, dance...
  clip: THREE.AnimationClip       // 动画剪辑
  loop: boolean                   // 是否循环
  speed: number                   // 播放速度 (1.0 = 正常)
}

interface AnimationTransition {
  from: string                    // 源状态
  to: string                      // 目标状态
  condition: () => boolean        // 转换条件
  duration: number                // 过渡时间（秒）
  interruptible: boolean          // 过渡中能否被打断
}
```

#### 状态机实现

```typescript
class AnimationStateMachine {
  private mixer: THREE.AnimationMixer
  private states: Map<string, AnimationState> = new Map()
  private transitions: AnimationTransition[] = []
  private currentState: AnimationState | null = null
  private currentAction: THREE.AnimationAction | null = null

  constructor(mixer: THREE.AnimationMixer) {
    this.mixer = mixer
  }

  addState(state: AnimationState): void {
    this.states.set(state.name, state)
  }

  addTransition(transition: AnimationTransition): void {
    this.transitions.push(transition)
  }

  play(stateName: string): void {
    const state = this.states.get(stateName)
    if (!state) return

    const action = this.mixer.clipAction(state.clip)
    action.setLoop(state.loop ? THREE.LoopRepeat : THREE.LoopOnce)
    action.setEffectiveTimeScale(state.speed)

    if (this.currentAction && this.currentAction !== action) {
      // 找到过渡配置
      const transition = this.transitions.find(
        t => t.from === this.currentState?.name && t.to === stateName
      )
      const duration = transition?.duration ?? 0.3
      this.currentAction.crossFadeTo(action, duration)
    }

    action.reset().play()
    this.currentAction = action
    this.currentState = state
  }

  update(delta: number): void {
    this.mixer.update(delta)
    // 检查自动转换条件
    for (const t of this.transitions) {
      if (this.currentState?.name === t.from && t.condition()) {
        this.play(t.to)
        break
      }
    }
  }
}
```

#### 典型状态机配置

```typescript
const stateMachine = new AnimationStateMachine(mixer)

// 注册状态
stateMachine.addState({ name: 'idle', clip: idleClip, loop: true, speed: 1.0 })
stateMachine.addState({ name: 'walk', clip: walkClip, loop: true, speed: 1.0 })
stateMachine.addState({ name: 'run', clip: runClip, loop: true, speed: 1.0 })
stateMachine.addState({ name: 'dance', clip: danceClip, loop: false, speed: 1.0 })

// 注册转换
stateMachine.addTransition({ from: 'idle', to: 'walk', condition: () => isMoving, duration: 0.3, interruptible: true })
stateMachine.addTransition({ from: 'walk', to: 'run', condition: () => isRunning, duration: 0.2, interruptible: true })
stateMachine.addTransition({ from: 'walk', to: 'idle', condition: () => !isMoving, duration: 0.5, interruptible: true })
stateMachine.addTransition({ from: 'idle', to: 'dance', condition: () => isDancing, duration: 0.4, interruptible: false })
```

### 3.10 视频舞蹈 → 3D 骨骼动画管线

> 补充 #3 和 #4：MediaPipe→3D 坐标转换 + MotionBERT 部署

#### Step 1：MediaPipe 2D 姿态估计

```python
# 安装: pip install mediapipe opencv-python
import mediapipe as mp
import cv2

mp_pose = mp.solutions.pose
pose = mp_pose.Pose(
    static_image_mode=False,
    model_complexity=1,        # 0=快速, 1=平衡, 2=精确
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

def extract_2d_keypoints(video_path: str) -> list:
    """从视频提取每帧 2D 关键点"""
    cap = cv2.VideoCapture(video_path)
    frames = []
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break
        results = pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        if results.pose_landmarks:
            keypoints = []
            for lm in results.pose_landmarks.landmark:
                keypoints.append([lm.x, lm.y, lm.z, lm.visibility])
            frames.append(keypoints)
    cap.release()
    return frames  # shape: [N_frames, 33, 4]
```

#### Step 2：2D→3D 坐标提升

**方案 A：简单三角测量（无 GPU）**

```python
import numpy as np

def estimate_depth_2d_to_3d(keypoints_2d: list, camera_fov: float = 60.0) -> list:
    """用人体比例启发式推断深度（不需要深度学习）"""
    # MediaPipe 输出已包含 z 值（相对深度），直接使用
    # z 值表示关节点相对于髋部的深度，范围约 [-0.5, 0.5]
    frames_3d = []
    for frame in keypoints_2d:
        joints = []
        for kp in frame:
            # 归一化坐标 → 世界坐标（假设人体高 1.7m）
            x = (kp[0] - 0.5) * 1.0   # 水平范围 ±0.5m
            y = (0.5 - kp[1]) * 1.7    # 垂直范围 0~1.7m
            z = kp[2] * 0.5            # 深度范围 ±0.25m
            joints.append([x, y, z])
        frames_3d.append(joints)
    return frames_3d
```

**方案 B：MotionBERT 深度学习（推荐，精度高）**

```bash
# 安装
git clone https://github.com/Walter0807/MotionBERT.git
pip install -r requirements.txt
# 下载预训练模型
wget https://huggingface.co/Walter0807/MotionBERT/resolve/main/finetuned_models/pose3d.pt
```

```python
from motionbert.utils.preprocess import pose2bbox
from motionbert.utils.infer import init_model, infer_video

def video_to_3d_pose(video_path: str) -> np.ndarray:
    """视频→3D 骨骼坐标"""
    model = init_model('pose3d.pt', device='cuda')
    pose_3d = infer_video(model, video_path)
    return pose_3d  # shape: [N_frames, 17, 3]
```

#### Step 3：3D 坐标 → BVH/JSON

```python
def pose_to_animation_json(pose_3d: np.ndarray, fps: int = 30) -> dict:
    """3D 骨骼坐标 → 动画 JSON"""
    # MotionBERT 输出 17 个关节点 (COCO 格式)
    # 需要映射到标准骨骼名
    JOINT_NAMES = [
        'hips', 'neck', 'nose',
        'left_shoulder', 'left_elbow', 'left_wrist',
        'right_shoulder', 'right_elbow', 'right_wrist',
        'left_hip', 'left_knee', 'left_ankle',
        'right_hip', 'right_knee', 'right_ankle',
        'left_eye', 'right_eye'
    ]
    
    frames = []
    for i, frame_joints in enumerate(pose_3d):
        bones = {}
        for j, name in enumerate(JOINT_NAMES):
            if j < len(frame_joints):
                bones[name] = {
                    'position': frame_joints[j].tolist(),
                    'rotation': [0, 0, 0, 1]  # 四元数，后续可从位置推算
                }
        frames.append({
            'timestamp': i / fps,
            'bones': bones
        })
    
    return {
        'name': 'video_dance',
        'duration': len(frames) / fps,
        'fps': fps,
        'bone_count': len(JOINT_NAMES),
        'frames': frames
    }
```

### 3.11 骨骼映射表（Mixamo ↔ PMX ↔ VRM）

> 补充 #5：完整的骨骼名称映射关系

#### Mixamo → PMX 映射（参考 Mixamo-MMD 项目）

```typescript
// Mixamo 标准骨骼名 → PMX/MMD 骨骼名
const MIXAMO_TO_PMX: Record<string, string> = {
  // 躯干
  'Hips': '下半身',
  'Spine': '上半身',
  'Spine1': '上半身1',
  'Spine2': '上半身2',
  'Neck': '首',
  'Head': '頭',
  
  // 左臂
  'LeftShoulder': '左肩',
  'LeftArm': '左腕',
  'LeftForeArm': '左ひじ',
  'LeftHand': '左手首',
  
  // 右臂
  'RightShoulder': '右肩',
  'RightArm': '右腕',
  'RightForeArm': '右ひじ',
  'RightHand': '右首首',
  
  // 左腿
  'LeftUpLeg': '左足',
  'LeftLeg': '左ひざ',
  'LeftFoot': '左足首',
  'LeftToeBase': '左つま先',
  
  // 右腿
  'RightUpLeg': '右足',
  'RightLeg': '右ひざ',
  'RightFoot': '右足首',
  'RightToeBase': '右つま先',
  
  // 手指
  'LeftHandThumb1': '左親指1',
  'LeftHandThumb2': '左親指2',
  'LeftHandIndex1': '左人指1',
  'LeftHandMiddle1': '左中指1',
  'RightHandThumb1': '右親指1',
  'RightHandIndex1': '右人指1',
  'RightHandMiddle1': '右中指1',
}
```

#### Mixamo → VRM 映射（参考 vrm-mixamo-retargeter）

```typescript
const MIXAMO_TO_VRM: Record<string, string> = {
  'Hips': 'hips',
  'Spine': 'spine',
  'Spine1': 'chest',
  'Spine2': 'upperChest',
  'Neck': 'neck',
  'Head': 'head',
  'LeftShoulder': 'leftShoulder',
  'LeftArm': 'leftUpperArm',
  'LeftForeArm': 'leftLowerArm',
  'LeftHand': 'leftHand',
  'RightShoulder': 'rightShoulder',
  'RightArm': 'rightUpperArm',
  'RightForeArm': 'rightLowerArm',
  'RightHand': 'rightHand',
  'LeftUpLeg': 'leftUpperLeg',
  'LeftLeg': 'leftLowerLeg',
  'LeftFoot': 'leftFoot',
  'RightUpLeg': 'rightUpperLeg',
  'RightLeg': 'rightLowerLeg',
  'RightFoot': 'rightFoot',
}
```

#### PMX → VRM 映射（组合推导）

```typescript
// PMX → Mixamo → VRM，两跳映射
function pmxToVrm(pmxBoneName: string): string | null {
  const mixamoName = Object.entries(MIXAMO_TO_PMX)
    .find(([_, v]) => v === pmxBoneName)?.[0]
  if (!mixamoName) return null
  return MIXAMO_TO_VRM[mixamoName] ?? null
}
```

### 3.12 视频动捕的参考项目

> 补充 #3 和 #4 的具体参考实现

| 项目 | 功能 | 链接 | 核心价值 |
|------|------|------|----------|
| **nlarion/mediapipe-to-bvh** | 视频→BVH | GitHub | 最简管线，MediaPipe 直接出 BVH |
| **VideoTo3dPoseAndBvh** | 视频→3D 姿态→BVH | GitHub | VideoPose3D + BVH 转换，完整管线 |
| **AmyangXYZ/Mixamo-MMD** | Mixamo FBX→VMD | GitHub | **关键**：在浏览器里把 Mixamo 动画转成 PMX 的 VMD 格式 |
| **saori-eth/vrm-mixamo-retargeter** | Mixamo→VRM 重定向 | GitHub | Mixamo 动画直接套到 VRM 模型 |
| **Walter0807/MotionBERT** | 视频→3D 骨骼 | GitHub | 最高精度的 3D 姿态估计 |
| **three-vrm examples** | VRM 动画播放 | 官方 | Mixamo 动画在 VRM 模型上播放的完整示例 |

#### 最快路径：Mixamo-MMD 集成

```
Mixamo 网站选动画 → 下载 FBX
  ↓
Mixamo-MMD 浏览器转换 → VMD 文件
  ↓
我们的 MMDLoader.loadWithAnimation(pmx, vmd)
  ↓
Three.js 播放动画 ✅
```

**不需要改骨骼、不需要 AI、不需要 Blender**，直接用 Mixamo 现成动画库。

### 3.13 PMX 模型接入标准骨骼

> 补充 #7：当前 PMX 模型怎么和 Mixamo/VRM 对接

#### 当前状态

```
PMX 模型 → MMDLoader → SkinnedMesh + Skeleton
  骨骼名：日文（頭、左腕、右ひじ...）
  动画：VMD 格式
```

#### 对接方案

**方案 A：Mixamo-MMD 转换（推荐起步）**

```
Mixamo 动画 FBX → Mixamo-MMD → VMD 文件
  ↓
MMDLoader.loadWithAnimation(pmxPath, vmdPath)
  ↓
Three.js 播放 ✅
```
- 优点：零代码改动，用现有 MMDLoader
- 缺点：需要预转换，不能实时重定向

**方案 B：骨骼映射表 + AnimationClip 重定向（推荐长期）**

```typescript
// 读取 PMX 骨骼名
const pmxBones = mesh.skeleton.bones.map(b => b.name)
// ['下半身', '上半身', '頭', '左腕', ...]

// 创建重定向后的 AnimationClip
function retargetClip(
  sourceClip: THREE.AnimationClip,
  boneMap: Record<string, string>
): THREE.AnimationClip {
  const newTracks = sourceClip.tracks.map(track => {
    // track.name 格式: '.bones[Hips].position'
    const match = track.name.match(/\.bones\[(.+?)\]\.(.+)/)
    if (!match) return track
    const [, sourceBoneName, property] = match
    const targetBoneName = boneMap[sourceBoneName]
    if (!targetBoneName) return null
    
    // 创建新的 track，替换骨骼名
    const newTrack = track.clone()
    newTrack.name = `.bones[${targetBoneName}].${property}`
    return newTrack
  }).filter(Boolean)
  
  return new THREE.AnimationClip(sourceClip.name, sourceClip.duration, newTracks)
}

// 使用
const mixamoClip = await loadMixamoFBX('dance.fbx')
const pmxClip = retargetClip(mixamoClip, MIXAMO_TO_PMX)
const action = mixer.clipAction(pmxClip)
action.play()
```

**方案 C：VRM 标准（长期）**

```
PMX 模型 → Blender VRM 插件 → 导出 VRM
  ↓
@pixiv/three-vrm 加载
  ↓
VRM Humanoid 标准骨骼
  ↓
Mixamo/VRM 动画直接复用
```

### 3.14 动画播放的 Agent 工具

> 补充 #6：Agent 工具完整 Schema

```json
{
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "play_animation",
        "description": "播放指定的骨骼动画。动画 ID 从动画库中查询。",
        "parameters": {
          "type": "object",
          "properties": {
            "animation_id": {
              "type": "string",
              "description": "动画 ID，如 'dance_hiphop', 'walk_normal', 'idle_breathing'"
            },
            "speed": {
              "type": "number",
              "description": "播放速度，默认 1.0",\n              "default": 1.0
            },
            "loop": {
              "type": "boolean",
              "description": "是否循环播放",
              "default": false
            },
            "transition_duration": {
              "type": "number",
              "description": "从当前动画过渡的时间（秒）",
              "default": 0.3
            }
          },
          "required": ["animation_id"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "stop_animation",
        "description": "停止当前动画，回到待机状态",
        "parameters": { "type": "object", "properties": {} }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "list_animations",
        "description": "查询可用动画列表",
        "parameters": {
          "type": "object",
          "properties": {
            "category": {
              "type": "string",
              "enum": ["idle", "walk", "dance", "emote", "all"],
              "description": "动画分类筛选"
            }
          }
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "upload_dance_video",
        "description": "上传舞蹈视频，AI 自动转换为骨骼动画",
        "parameters": {
          "type": "object",
          "properties": {
            "video_path": {
              "type": "string",
              "description": "视频文件路径"
            },
            "name": {
              "type": "string",
              "description": "动画名称"
            },
            "auto_segment": {
              "type": "boolean",
              "description": "是否自动分段",
              "default": true
            }
          },
          "required": ["video_path"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "set_idle_animation",
        "description": "设置宠物的默认待机动画",
        "parameters": {
          "type": "object",
          "properties": {
            "animation_id": {
              "type": "string",
              "description": "待机动画 ID"
            }
          },
          "required": ["animation_id"]
        }
      }
    }
  ]
}
```

### 3.15 补充完整性检查清单

| # | 缺失项 | 对应章节 | 状态 |
|---|--------|---------|------|
| 1 | 动画数据 JSON Schema | §3.8 | ✅ 已补充 |
| 2 | 动画状态机实现 | §3.9 | ✅ 已补充 |
| 3 | MediaPipe→3D 坐标转换 | §3.10 Step 1-2 | ✅ 已补充 |
| 4 | MotionBERT 部署和调用 | §3.10 Step 2 方案 B | ✅ 已补充 |
| 5 | 骨骼映射表 | §3.11 | ✅ 已补充 |
| 6 | Agent 工具 Schema | §3.14 | ✅ 已补充 |
| 7 | PMX 接入标准骨骼 | §3.13 | ✅ 已补充 |
| — | 视频动捕参考项目 | §3.12 | ✅ 额外补充 |

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

> 详细任务拆解见文档顶部「零、开发任务清单」。
> 以下为阶段概览，每阶段包含具体任务 ID。

| 阶段 | 任务 | 预计 | 验收标准 |
|------|------|------|--------|
| 阶段 1 | T1 积木类型 + T2 场景构建器 + T4 脚本引擎 | 4 天 | 手动调用 API 能构建简单房子 |
| 阶段 2 | T3 Agent 工具 + T5 后端 API | 2 天 | 用户说「建一个木屋」→ Agent 自动生成脚本并构建 |
| 阶段 3 | T6 动画系统 + T7 骨骼映射 | 3 天 | Mixamo 动画在 PMX 模型上播放 |
| 阶段 4 | T8 视频动捕 | 3 天 | 上传舞蹈视频 → 宠物播放动画 |
| 阶段 5 | T9 前端集成 + T10 测试 | 3 天 | 端到端验收通过 |

---

## 九、技术参考

| 项目/论文 | 来源 | 核心价值 | 链接 |
|----------|------|---------|------|
| 3D-GPT | 论文 | LLM 生成程序化建模脚本的框架 | arxiv 2310.12945 |
| PSP | SIGGRAPH Asia 2025 | 程序化场景描述语言（PSDL） | — |
| SceneGenAgent | 论文 | Agent + PCG 结合 | — |
| Mixamo-MMD | GitHub | Mixamo FBX→VMD 转换，打通 Mixamo→PMX 链路 | AmyangXYZ/Mixamo-MMD |
| vrm-mixamo-retargeter | GitHub | Mixamo 动画→VRM 模型重定向 | saori-eth/vrm-mixamo-retargeter |
| mediapipe-to-bvh | GitHub | 视频→BVH 动画文件 | nlarion/mediapipe-to-bvh |
| MotionBERT | GitHub | 视频→3D 骨骼坐标（最高精度） | Walter0807/MotionBERT |
| three-vrm | GitHub | VRM 模型加载+动画播放 | pixiv/three-vrm |
| lo-th/3d.city | GitHub | Three.js 城市建造游戏 | lo-th/3d.city |
| tiveor/city-simulator | GitHub | React Three Fiber 城市模拟器 | tiveor/city-simulator |
| qonqulab/voxelcraft | GitHub | 网页版 Minecraft 体素引擎 | qonqulab/voxelcraft |
| Three.js r185 | 官方 | InstancedMesh / WebGPU / TSL / 后处理 | three.js.org |

---

## 十、风险与约束

| 风险 | 影响 | 缓解措施 |
|------|------|--------|
| Agent 生成的脚本质量不稳定 | 场景可能不美观 | 提供预制模板 + 约束规则 |
| 积木种类不够丰富 | 场景单调 | 渐进扩充积木库 + 支持外部模型 |
| 性能瓶颈（大量积木） | 渲染卡顿 | InstancedMesh + 场景分区 + LOD |
| 场景序列化体积大 | 保存/加载慢 | 只序列化增量操作（脚本而非快照） |
| Agent 工具调用延迟 | 用户等待时间长 | 流式生成 + 渐进渲染 |
| PMX 骨骼名日文 | 映射表维护成本 | Mixamo-MMD 已有完整映射，直接复用 |
| MotionBERT GPU 依赖 | 无 GPU 时处理慢 | 提供 MediaPipe 简化方案作为 fallback |

---

> **下一步**：从 T1 开始实施。中断后查看顶部「进度追踪」表，从下一个未完成任务继续。
