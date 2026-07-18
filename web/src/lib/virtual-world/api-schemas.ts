/**
 * Backend API Schemas — 后端 API 数据结构定义
 *
 * 对应文档：agent-3d-building-block-system.md §3.8, §6.3
 * 定义场景/动画相关的 Pydantic schema 和数据库表结构。
 *
 * 注意：这些是 TypeScript 等价定义，用于前端与后端对齐。
 * 后端实际使用 Python Pydantic + SQLAlchemy。
 */

// ---------------------------------------------------------------------------
// 场景 API
// ---------------------------------------------------------------------------

// 复用 scene-builder 的 SceneBlockData，不重复定义
export type { SceneBlockData } from './scene-builder'

/** POST /api/v1/pet/scene/build 请求体 */
export interface SceneBuildRequest {
  script: {
    version: string
    name: string
    description?: string
    actions: Array<{
      tool: string
      params: Record<string, unknown>
    }>
  }
}

/** POST /api/v1/pet/scene/build 响应体 */
export interface SceneBuildResponse {
  success: boolean
  scriptName: string
  totalActions: number
  executedActions: number
  errors: Array<{
    index: number
    tool: string
    error: string
  }>
  durationMs: number
}

/** GET /api/v1/pet/scene/info 响应体 */
export interface SceneInfoResponse {
  blockCount: number
  bounds: {
    minX: number
    maxX: number
    minZ: number
    maxZ: number
  } | null
  blocks: SceneBlockData[]
}

/** POST /api/v1/pet/scene/reset 响应体 */
export interface SceneResetResponse {
  success: boolean
}

/** POST /api/v1/pet/scene/generate 请求体 */
export interface SceneGenerateRequest {
  prompt: string
  style?: string
}

/** POST /api/v1/pet/scene/generate 响应体 */
export interface SceneGenerateResponse {
  success: boolean
  script: SceneBuildRequest['script']
  buildResult: SceneBuildResponse
}

// ---------------------------------------------------------------------------
// 动画 API
// ---------------------------------------------------------------------------

/** 动画元数据（数据库记录） */
export interface AnimationMeta {
  id: number
  name: string
  filePath: string
  duration: number        // 秒
  fps: number
  boneCount: number
  category: 'idle' | 'walk' | 'dance' | 'emote' | 'custom'
  source: 'mixamo' | 'video' | 'ai'
  createdAt: string       // ISO datetime
  updatedAt: string
}

/** POST /api/v1/pet/animation/upload 请求体 */
export interface AnimationUploadRequest {
  name: string
  category?: AnimationMeta['category']
  source?: AnimationMeta['source']
}

/** GET /api/v1/pet/animation/list 响应体 */
export interface AnimationListResponse {
  animations: AnimationMeta[]
  total: number
}

/** POST /api/v1/pet/animation/play 请求体 */
export interface AnimationPlayRequest {
  animationId: number
  speed?: number
  loop?: boolean
  transitionDuration?: number
}

/** POST /api/v1/pet/animation/stop 响应体 */
export interface AnimationStopResponse {
  success: boolean
}

// ---------------------------------------------------------------------------
// 数据库表结构（SQLAlchemy 等价 TypeScript 定义）
// ---------------------------------------------------------------------------

/**
 * pet_scene 表 — 场景持久化
 *
 * CREATE TABLE pet_scene (
 *   id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
 *   name        VARCHAR(100) NOT NULL DEFAULT '',
 *   description VARCHAR(500) NOT NULL DEFAULT '',
 *   script_json JSON NOT NULL,
 *   blocks_json JSON NOT NULL,
 *   is_default  TINYINT UNSIGNED NOT NULL DEFAULT 0,
 *   created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
 *   updated_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
 *   is_deleted  TINYINT UNSIGNED NOT NULL DEFAULT 0
 * );
 */

/**
 * pet_animation 表 — 动画元数据
 *
 * CREATE TABLE pet_animation (
 *   id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
 *   name        VARCHAR(100) NOT NULL COMMENT '动画名称',
 *   file_path   VARCHAR(500) NOT NULL COMMENT 'JSON/BVH/FBX 文件路径',
 *   duration    DECIMAL(10,2) NOT NULL COMMENT '时长(秒)',
 *   fps         INT NOT NULL DEFAULT 30 COMMENT '帧率',
 *   bone_count  INT NOT NULL COMMENT '骨骼数',
 *   category    VARCHAR(50) NOT NULL DEFAULT 'custom' COMMENT '分类: idle/walk/dance/emote/custom',
 *   source      VARCHAR(50) NOT NULL DEFAULT 'mixamo' COMMENT '来源: mixamo/video/ai',
 *   created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
 *   updated_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
 *   is_deleted  TINYINT UNSIGNED NOT NULL DEFAULT 0
 * );
 */

// ---------------------------------------------------------------------------
// API 端点常量
// ---------------------------------------------------------------------------

export const SCENE_ENDPOINTS = {
  BUILD: '/api/v1/pet/scene/build',
  INFO: '/api/v1/pet/scene/info',
  RESET: '/api/v1/pet/scene/reset',
  GENERATE: '/api/v1/pet/scene/generate',
} as const

export const ANIMATION_ENDPOINTS = {
  UPLOAD: '/api/v1/pet/animation/upload',
  LIST: '/api/v1/pet/animation/list',
  PLAY: '/api/v1/pet/animation/play',
  STOP: '/api/v1/pet/animation/stop',
} as const
