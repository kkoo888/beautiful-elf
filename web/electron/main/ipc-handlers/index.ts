import { registerWindowHandlers } from './window'
import { registerPetHandlers } from './pet'
import { registerAppHandlers } from './app'

/**
 * 统一注册所有 IPC handlers
 * 按模块拆分，便于维护和扩展
 */
export function registerIpcHandlers(): void {
  registerWindowHandlers()
  registerAppHandlers()
  registerPetHandlers()
}
