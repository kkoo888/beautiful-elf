/**
 * 通用类型定义
 */

/** 选项类型（用于 Select/Dropdown 等） */
export interface Option<T = string> {
  label: string
  value: T
  disabled?: boolean
}

/** 树节点类型（用于 Tree 组件） */
export interface TreeNode<T = unknown> {
  key: string
  title: string
  children?: TreeNode<T>[]
  data?: T
  isLeaf?: boolean
}

/** 键值对 */
export interface KeyValuePair<K = string, V = unknown> {
  key: K
  value: V
}

/** 操作结果 */
export interface OperationResult<T = void> {
  success: boolean
  data?: T
  error?: string
}

/** 时间范围 */
export interface TimeRange {
  start: string
  end: string
}

/** 文件信息 */
export interface FileInfo {
  name: string
  size: number
  type: string
  lastModified: number
}

/** 坐标点 */
export interface Point {
  x: number
  y: number
}

/** 矩形区域 */
export interface Rect extends Point {
  width: number
  height: number
}

/** 主题模式 */
export type ThemeMode = 'light' | 'dark' | 'high-contrast'

/** 网络状态 */
export type NetworkStatus = 'online' | 'offline' | 'syncing'
