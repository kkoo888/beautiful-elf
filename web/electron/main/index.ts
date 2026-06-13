import { app, shell } from 'electron'
import { electronApp, optimizer } from '@electron-toolkit/utils'
import { createMainWindow, getMainWindow } from './window-manager'
import { createTray } from './tray'
import { registerIpcHandlers } from './ipc-handlers'
import { createChineseMenu } from './menu'
import './pet-window'

app.whenReady().then(() => {
  electronApp.setAppUserModelId('com.beautiful-elf')

  app.on('browser-window-created', (_, window) => {
    optimizer.watchWindowShortcuts(window)
  })

  const mainWindow = createMainWindow()
  // 确保宠物窗口一定会被创建（即使 ready-to-show 不触发）
  import('./pet-window').then(({ createPetWindow, getPetWindow }) => {
    if (!getPetWindow()) {
      createPetWindow()
    }
  })
  createChineseMenu(mainWindow)
  createTray(mainWindow)
  registerIpcHandlers()

  // 外部链接用系统浏览器打开
  mainWindow.webContents.setWindowOpenHandler((details) => {
    shell.openExternal(details.url)
    return { action: 'deny' }
  })

  app.on('activate', () => {
    if (getMainWindow() === null) createMainWindow()
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})
