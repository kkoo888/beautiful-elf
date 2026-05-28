/**
 * 数据管理组件
 * 支持数据导出、导入和清除
 */

import { useCallback, useState } from 'react'
import { Button, Card, Upload, message, Space, Typography, Divider, Alert, Popconfirm } from 'antd'
import { DownloadOutlined, UploadOutlined, DeleteOutlined } from '@ant-design/icons'
import type { UploadProps } from 'antd'
import styles from './settings-panel.module.css'

const { Text, Title, Paragraph } = Typography

/** 导出数据格式 */
export interface ExportData {
  version: string
  exportedAt: number
  data: Record<string, unknown>
}

/** 应用数据 localStorage 键前缀 */
const DATA_PREFIX = 'beautiful-elf:'

/** 当前导出格式版本 */
const EXPORT_VERSION = '1.0.0'

/**
 * 导出数据为 JSON 文件并下载
 */
export function exportToFile(data: ExportData, filename: string): void {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

/**
 * 从 JSON 文件解析导入数据
 */
export function importFromFile(file: File): Promise<ExportData> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      try {
        const parsed = JSON.parse(reader.result as string)
        if (!parsed.version || !parsed.data) {
          reject(new Error('文件格式不正确：缺少 version 或 data 字段'))
          return
        }
        resolve(parsed as ExportData)
      } catch {
        reject(new Error('无效的 JSON 文件'))
      }
    }
    reader.onerror = reject
    reader.readAsText(file)
  })
}

/**
 * 收集所有 beautiful-elf: 开头的 localStorage 数据
 */
function collectAllData(): Record<string, unknown> {
  const data: Record<string, unknown> = {}
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i)
    if (key && key.startsWith(DATA_PREFIX)) {
      try {
        data[key] = JSON.parse(localStorage.getItem(key) ?? 'null')
      } catch {
        data[key] = localStorage.getItem(key)
      }
    }
  }
  return data
}

/**
 * 将导入数据写入 localStorage
 */
function restoreAllData(data: Record<string, unknown>): void {
  for (const [key, value] of Object.entries(data)) {
    if (key.startsWith(DATA_PREFIX)) {
      localStorage.setItem(key, typeof value === 'string' ? value : JSON.stringify(value))
    }
  }
}

/**
 * 清除所有 beautiful-elf: 开头的 localStorage 数据
 */
function clearAllData(): void {
  const keysToRemove: string[] = []
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i)
    if (key && key.startsWith(DATA_PREFIX)) {
      keysToRemove.push(key)
    }
  }
  keysToRemove.forEach((key) => localStorage.removeItem(key))
}

/** 生成带日期的导出文件名 */
function getExportFilename(): string {
  const now = new Date()
  const date = now.toISOString().slice(0, 10)
  return `beautiful-elf-backup-${date}.json`
}

/** 数据管理面板 */
export function DataManagement() {
  const [importing, setImporting] = useState(false)

  /** 导出数据 */
  const handleExport = useCallback(() => {
    try {
      const data = collectAllData()
      const exportData: ExportData = {
        version: EXPORT_VERSION,
        exportedAt: Date.now(),
        data,
      }
      exportToFile(exportData, getExportFilename())
      message.success('数据导出成功')
    } catch {
      message.error('数据导出失败')
    }
  }, [])

  /** 导入数据 */
  const handleImport = useCallback<NonNullable<UploadProps['beforeUpload']>>(async (file) => {
    setImporting(true)
    try {
      const imported = await importFromFile(file)
      restoreAllData(imported.data)
      message.success(`数据导入成功（版本: ${imported.version}）`)
      // 刷新页面以加载新数据
      setTimeout(() => window.location.reload(), 800)
    } catch (err) {
      message.error(`导入失败: ${err instanceof Error ? err.message : '未知错误'}`)
    } finally {
      setImporting(false)
    }
    return false // 阻止 Upload 自动上传
  }, [])

  /** 清除数据 */
  const handleClear = useCallback(() => {
    try {
      clearAllData()
      message.success('所有数据已清除')
      setTimeout(() => window.location.reload(), 800)
    } catch {
      message.error('清除数据失败')
    }
  }, [])

  return (
    <div>
      <Title level={5}>数据管理</Title>
      <Paragraph type="secondary">
        导出或导入应用数据，方便备份和迁移。所有数据存储在本地浏览器中。
      </Paragraph>

      {/* 导出 */}
      <Card size="small" title="📦 导出数据" style={{ marginBottom: 16 }}>
        <Paragraph type="secondary">
          将所有本地数据（设置、对话、灵魂配置等）打包为 JSON 文件下载。
        </Paragraph>
        <Button type="primary" icon={<DownloadOutlined />} onClick={handleExport}>
          导出备份文件
        </Button>
      </Card>

      {/* 导入 */}
      <Card size="small" title="📥 导入数据" style={{ marginBottom: 16 }}>
        <Paragraph type="secondary">
          上传之前导出的 JSON 备份文件，将数据导入到当前浏览器。导入后页面会自动刷新。
        </Paragraph>
        <Upload
          accept=".json"
          showUploadList={false}
          beforeUpload={handleImport}
          disabled={importing}
        >
          <Button icon={<UploadOutlined />} loading={importing}>
            选择备份文件
          </Button>
        </Upload>
      </Card>

      <Divider />

      {/* 清除 */}
      <Card size="small" title="🗑️ 清除数据" style={{ marginBottom: 16 }}>
        <Alert
          message="危险操作"
          description="清除后所有本地数据将丢失且无法恢复，建议先导出备份。"
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
        />
        <Popconfirm
          title="确认清除所有数据？"
          description="此操作不可撤销，所有设置、对话记录和配置将被永久删除。"
          onConfirm={handleClear}
          okText="确认清除"
          cancelText="取消"
          okButtonProps={{ danger: true }}
        >
          <Button danger icon={<DeleteOutlined />}>
            清除所有数据
          </Button>
        </Popconfirm>
      </Card>
    </div>
  )
}
