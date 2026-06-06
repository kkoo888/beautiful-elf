/**
 * API 契约 - 前后端共享类型
 *
 * @deprecated 请直接使用 web/src/renderer/types/index.ts 中的类型定义。
 *             后端 CamelModel 已统一返回 camelCase，本文件保留仅为兼容。
 */

// Re-export 统一类型（camelCase）
export type { ApiResponse, PaginatedResponse, PaginationParams } from '@/types/api'
