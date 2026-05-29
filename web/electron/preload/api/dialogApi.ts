import { ipcRenderer } from 'electron'

/** 系统对话框 API */
export const dialogApi = {
  /** 选择目录，返回路径或 null（用户取消） */
  selectDirectory: (): Promise<string | null> =>
    ipcRenderer.invoke('dialog:selectDirectory'),
}
