/**
 * Virtual World — 统一导出
 *
 * 所有 3D 虚拟世界模块的入口文件。
 */
// 积木系统
export { BLOCK_TYPES, type BlockType, type GeometryConfig, createBlockGeometry, getBlocksByCategory, getBlocksByTag } from './block-registry'
export { type MaterialConfig, createMaterial, createMaterialInstance, getMaterialConfig, listMaterialIds, disposeMaterialCache } from './materials'

// 场景
export { SceneBuilder, type SceneBlockData } from './scene-builder'

// 工具 & 脚本
export { SceneToolRegistry, type SceneTool, type ToolParameter, createDefaultToolRegistry } from './scene-tools'
export { ScriptExecutor, type SceneBuildScript, type SceneAction, type ExecutionResult, validateScript, loadScriptFromUrl } from './script-executor'

// 动画
export { AnimationManager } from './animation-manager'
export { AnimationStateMachine, type AnimationState, type AnimationTransition } from './animation-state-machine'
export { type AnimationData, type FrameData, type BoneFrameData, loadAnimationFromJson, parseAnimationData, loadAnimations, getClipBoneNames, validateAnimationData } from './animation-loader'

// 骨骼重定向
export { MIXAMO_TO_PMX, MIXAMO_TO_VRM, PMX_TO_MIXAMO, VRM_TO_MIXAMO, type BoneMapping, type RetargetOptions, retargetClip, retargetMixamoToPmx, retargetMixamoToVrm, retargetPmxToMixamo, getBoneNames, checkCompatibility, pmxToVrm, vrmToPmx } from './bone-retargeter'

// API Schemas
export { type SceneBuildRequest, type SceneBuildResponse, type SceneInfoResponse, type SceneResetResponse, type SceneGenerateRequest, type SceneGenerateResponse, type AnimationMeta, type AnimationUploadRequest, type AnimationListResponse, type AnimationPlayRequest, type AnimationStopResponse, SCENE_ENDPOINTS, ANIMATION_ENDPOINTS } from './api-schemas'

// 集成入口
export { PetWorld, type PetWorldOptions } from './pet-world'
