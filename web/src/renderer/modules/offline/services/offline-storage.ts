/** IndexedDB 离线存储服务（原生 API，无依赖） */

import type { OfflineMessage, OfflineStorageStats } from '../types/offline'

const DB_NAME = 'beautiful-elf-offline'
const DB_VERSION = 1
const STORE_NAME = 'offline-messages'

/** 打开/创建数据库 */
function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION)

    request.onupgradeneeded = () => {
      const db = request.result
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        const store = db.createObjectStore(STORE_NAME, { keyPath: 'id' })
        store.createIndex('status', 'status', { unique: false })
        store.createIndex('createdAt', 'createdAt', { unique: false })
      }
    }

    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error)
  })
}

/** 获取 ObjectStore (readonly/readonly) */
async function getStore(mode: IDBTransactionMode = 'readonly'): Promise<IDBObjectStore> {
  const db = await openDB()
  const tx = db.transaction(STORE_NAME, mode)
  return tx.objectStore(STORE_NAME)
}

/** 保存离线消息 */
export async function saveMessage(msg: OfflineMessage): Promise<void> {
  const store = await getStore('readwrite')
  return new Promise((resolve, reject) => {
    const req = store.put(msg)
    req.onsuccess = () => resolve()
    req.onerror = () => reject(req.error)
  })
}

/** 获取所有待发送消息 */
export async function getPendingMessages(): Promise<OfflineMessage[]> {
  const store = await getStore('readonly')
  return new Promise((resolve, reject) => {
    const index = store.index('status')
    const req = index.getAll('pending')
    req.onsuccess = () => resolve(req.result as OfflineMessage[])
    req.onerror = () => reject(req.error)
  })
}

/** 删除已发送消息 */
export async function deleteMessage(id: string): Promise<void> {
  const store = await getStore('readwrite')
  return new Promise((resolve, reject) => {
    const req = store.delete(id)
    req.onsuccess = () => resolve()
    req.onerror = () => reject(req.error)
  })
}

/** 获取所有消息 */
export async function getAllMessages(): Promise<OfflineMessage[]> {
  const store = await getStore('readonly')
  return new Promise((resolve, reject) => {
    const req = store.getAll()
    req.onsuccess = () => resolve(req.result as OfflineMessage[])
    req.onerror = () => reject(req.error)
  })
}

/** 清空所有离线数据 */
export async function clearAll(): Promise<void> {
  const store = await getStore('readwrite')
  return new Promise((resolve, reject) => {
    const req = store.clear()
    req.onsuccess = () => resolve()
    req.onerror = () => reject(req.error)
  })
}

/** 获取存储统计 */
export async function getStorageStats(): Promise<OfflineStorageStats> {
  const messages = await getAllMessages()
  const sizeBytes = new Blob([JSON.stringify(messages)]).size
  return { count: messages.length, sizeBytes }
}
