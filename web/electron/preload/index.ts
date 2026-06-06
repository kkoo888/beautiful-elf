import { contextBridge } from 'electron'
import { electronAPI } from './api'

// 安全地暴露 API 给渲染进程
contextBridge.exposeInMainWorld('electronAPI', electronAPI)
