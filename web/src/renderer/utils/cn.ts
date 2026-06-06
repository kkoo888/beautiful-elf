/**
 * className 合并工具
 * 简单实现：过滤 falsy 值，用空格拼接
 */
export function cn(...classes: (string | undefined | null | false)[]): string {
  return classes.filter(Boolean).join(' ')
}
