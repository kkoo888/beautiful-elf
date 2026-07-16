/**
 * 头像工具函数
 */

/**
 * 将头像路径转换为完整 URL
 * @param path 相对路径，如 "uploads/avatars/avatar_xxxx.png"
 * @returns 完整 URL，如 "http://localhost:6680/uploads/avatars/avatar_xxxx.png"
 */
export function toAvatarUrl(path: string): string {
  if (!path) return ''
  
  // 如果已经是完整 URL，直接返回
  if (path.startsWith('http')) return path
  
  // 如果是 base64 data URI（旧数据），直接返回
  if (path.startsWith('data:')) return path
  
  // 构建完整 URL
  const baseUrl = `http://${import.meta.env.VITE_API_HOST || 'localhost'}:${import.meta.env.VITE_API_PORT || '6680'}`
  return `${baseUrl}/${path}`
}
