import { ipcMain, dialog } from 'electron'

/** 注册对话框相关 IPC handlers */
export function registerDialogHandlers(): void {
  /** 选择目录 */
  ipcMain.handle('dialog:selectDirectory', async () => {
    const result = await dialog.showOpenDialog({
      properties: ['openDirectory'],
      title: '选择模型目录',
      buttonLabel: '选择',
    })
    if (result.canceled || result.filePaths.length === 0) {
      return null
    }
    return result.filePaths[0]
  })
}
