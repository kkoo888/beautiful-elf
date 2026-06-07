/**
 * Ant Design v6 推荐的 message 获取方式
 * 替代静态 import { message } from 'antd'
 *
 * 用法：const { message } = useMessage()
 */
import { App } from 'antd'

export function useMessage() {
  return App.useApp()
}
