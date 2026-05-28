/**
 * 离线消息队列 - 基于 IndexedDB
 * 断网时消息暂存，恢复后自动发送
 */

import type { QueuedMessage, WSMessage } from './types'

const DB_NAME = 'beautiful-elf-ws'
const DB_VERSION = 1
const STORE_NAME = 'message-queue'
const MAX_MESSAGES = 500

function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION)

    request.onupgradeneeded = () => {
      const db = request.result
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        const store = db.createObjectStore(STORE_NAME, { keyPath: 'id' })
        store.createIndex('createdAt', 'createdAt', { unique: false })
      }
    }

    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error)
  })
}

function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
}

/**
 * 消息队列管理器
 * 使用原生 IndexedDB API，无额外依赖
 */
export class MessageQueue {
  private db: IDBDatabase | null = null
  private initPromise: Promise<void> | null = null

  /** 初始化 IndexedDB 连接 */
  async init(): Promise<void> {
    if (this.db) return
    if (this.initPromise) return this.initPromise

    this.initPromise = openDB().then((db) => {
      this.db = db
    })

    return this.initPromise
  }

  /** 确保 DB 已初始化 */
  private async ensureDB(): Promise<IDBDatabase> {
    if (!this.db) {
      await this.init()
    }
    if (!this.db) {
      throw new Error('Failed to open IndexedDB')
    }
    return this.db
  }

  /** 入队一条消息 */
  async enqueue(message: WSMessage): Promise<string> {
    const db = await this.ensureDB()
    const id = generateId()
    const queued: QueuedMessage = {
      id,
      message,
      createdAt: Date.now(),
      retryCount: 0,
    }

    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readwrite')
      const store = tx.objectStore(STORE_NAME)
      const req = store.add(queued)

      req.onsuccess = () => {
        this.trimExcess()
        resolve(id)
      }
      req.onerror = () => reject(req.error)
    })
  }

  /** 取出所有排队消息 */
  async dequeueAll(): Promise<QueuedMessage[]> {
    const db = await this.ensureDB()

    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readonly')
      const store = tx.objectStore(STORE_NAME)
      const req = store.getAll()

      req.onsuccess = () => resolve(req.result as QueuedMessage[])
      req.onerror = () => reject(req.error)
    })
  }

  /** 删除指定消息 */
  async remove(id: string): Promise<void> {
    const db = await this.ensureDB()

    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readwrite')
      const store = tx.objectStore(STORE_NAME)
      const req = store.delete(id)

      req.onsuccess = () => resolve()
      req.onerror = () => reject(req.error)
    })
  }

  /** 清空队列 */
  async clear(): Promise<void> {
    const db = await this.ensureDB()

    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readwrite')
      const store = tx.objectStore(STORE_NAME)
      const req = store.clear()

      req.onsuccess = () => resolve()
      req.onerror = () => reject(req.error)
    })
  }

  /** 获取队列长度 */
  async size(): Promise<number> {
    const db = await this.ensureDB()

    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readonly')
      const store = tx.objectStore(STORE_NAME)
      const req = store.count()

      req.onsuccess = () => resolve(req.result)
      req.onerror = () => reject(req.error)
    })
  }

  /** 增加重试计数 */
  async incrementRetry(id: string): Promise<void> {
    const db = await this.ensureDB()

    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readwrite')
      const store = tx.objectStore(STORE_NAME)
      const getReq = store.get(id)

      getReq.onsuccess = () => {
        const item = getReq.result as QueuedMessage | undefined
        if (item) {
          item.retryCount += 1
          store.put(item)
        }
        resolve()
      }
      getReq.onerror = () => reject(getReq.error)
    })
  }

  /** 裁剪超出上限的消息（FIFO 淘汰最旧的） */
  private async trimExcess(): Promise<void> {
    const db = await this.ensureDB()

    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readwrite')
      const store = tx.objectStore(STORE_NAME)
      const countReq = store.count()

      countReq.onsuccess = () => {
        const total = countReq.result
        if (total <= MAX_MESSAGES) {
          resolve()
          return
        }

        const toDelete = total - MAX_MESSAGES
        const index = store.index('createdAt')
        const cursorReq = index.openCursor()
        let deleted = 0

        cursorReq.onsuccess = () => {
          const cursor = cursorReq.result
          if (cursor && deleted < toDelete) {
            cursor.delete()
            deleted++
            cursor.continue()
          } else {
            resolve()
          }
        }
        cursorReq.onerror = () => reject(cursorReq.error)
      }
      countReq.onerror = () => reject(countReq.error)
    })
  }

  /** 关闭 DB 连接 */
  close(): void {
    if (this.db) {
      this.db.close()
      this.db = null
      this.initPromise = null
    }
  }
}
