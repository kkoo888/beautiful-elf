/** IndexedDB 离线存储服务（使用 idb 库） */

import { openDB, type IDBPDatabase } from 'idb'
import type { OfflineMessage, OfflineStorageStats } from '../types/offline'

const DB_NAME = 'beautiful-elf-offline'
const DB_VERSION = 1
const STORE_NAME = 'messages'
const MAX_MESSAGES = 500
const MAX_SIZE_BYTES = 10 * 1024 * 1024 // 10MB

/** 数据库 Schema 定义 */
interface OfflineDBSchema {
  messages: {
    key: string
    value: OfflineMessage
    indexes: {
      'by-created': number
      'by-status': string
    }
  }
}

let dbInstance: IDBPDatabase<OfflineDBSchema> | null = null

/** 获取数据库实例（单例） */
async function getDB(): Promise<IDBPDatabase<OfflineDBSchema>> {
  if (dbInstance) return dbInstance

  dbInstance = await openDB<OfflineDBSchema>(DB_NAME, DB_VERSION, {
    upgrade(db) {
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        const store = db.createObjectStore(STORE_NAME, { keyPath: 'id' })
        store.createIndex('by-created', 'createdAt')
        store.createIndex('by-status', 'status')
      }
    },
  })

  return dbInstance
}

/** 添加消息（带 FIFO 淘汰） */
export async function addMessage(msg: OfflineMessage): Promise<void> {
  const db = await getDB()

  // 检查存储上限，执行 FIFO 淘汰
  await evictIfNeeded(db)

  await db.put(STORE_NAME, msg)
}

/** 获取所有消息（按 createdAt 升序） */
export async function getMessages(): Promise<OfflineMessage[]> {
  const db = await getDB()
  return db.getAllFromIndex(STORE_NAME, 'by-created')
}

/** 获取指定状态的消息 */
export async function getMessagesByStatus(
  status: OfflineMessage['status']
): Promise<OfflineMessage[]> {
  const db = await getDB()
  return db.getAllFromIndex(STORE_NAME, 'by-status', status)
}

/** 删除消息 */
export async function deleteMessage(id: string): Promise<void> {
  const db = await getDB()
  await db.delete(STORE_NAME, id)
}

/** 清除已发送消息（status === 'pending' 之外的都清除） */
export async function clearSent(): Promise<void> {
  const db = await getDB()
  const tx = db.transaction(STORE_NAME, 'readwrite')
  const store = tx.objectStore(STORE_NAME)
  let cursor = await store.openCursor()

  while (cursor) {
    if (cursor.value.status !== 'pending') {
      await cursor.delete()
    }
    cursor = await cursor.continue()
  }

  await tx.done
}

/** 更新消息状态 */
export async function updateMessageStatus(
  id: string,
  status: OfflineMessage['status']
): Promise<void> {
  const db = await getDB()
  const msg = await db.get(STORE_NAME, id)
  if (msg) {
    msg.status = status
    if (status === 'failed') {
      msg.retryCount += 1
    }
    await db.put(STORE_NAME, msg)
  }
}

/** 获取存储统计 */
export async function getStorageSize(): Promise<OfflineStorageStats> {
  const db = await getDB()
  const allMessages = await db.getAll(STORE_NAME)
  const sizeBytes = new Blob([JSON.stringify(allMessages)]).size
  return { count: allMessages.length, sizeBytes }
}

/** 获取消息总数 */
export async function getMessageCount(): Promise<number> {
  const db = await getDB()
  return db.count(STORE_NAME)
}

/** FIFO 淘汰：超过 500 条或 10MB 时删除最旧的 */
async function evictIfNeeded(db: IDBPDatabase<OfflineDBSchema>): Promise<void> {
  const count = await db.count(STORE_NAME)

  // 按消息数淘汰
  if (count >= MAX_MESSAGES) {
    const toEvict = count - MAX_MESSAGES + 1
    const oldest = await db.getAllFromIndex(STORE_NAME, 'by-created')
    const tx = db.transaction(STORE_NAME, 'readwrite')
    for (let i = 0; i < toEvict && i < oldest.length; i++) {
      await tx.store.delete(oldest[i].id)
    }
    await tx.done
    return
  }

  // 按大小淘汰（仅在接近上限时检查，避免频繁计算）
  if (count > MAX_MESSAGES * 0.8) {
    const allMessages = await db.getAll(STORE_NAME)
    const sizeBytes = new Blob([JSON.stringify(allMessages)]).size

    if (sizeBytes > MAX_SIZE_BYTES) {
      // 删除最旧的直到低于 90% 上限
      const targetSize = MAX_SIZE_BYTES * 0.9
      let currentSize = sizeBytes
      const sorted = allMessages.sort((a, b) => a.createdAt - b.createdAt)
      const tx = db.transaction(STORE_NAME, 'readwrite')

      for (const msg of sorted) {
        if (currentSize <= targetSize) break
        const msgSize = new Blob([JSON.stringify(msg)]).size
        await tx.store.delete(msg.id)
        currentSize -= msgSize
      }

      await tx.done
    }
  }
}
