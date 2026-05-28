import { useCallback, useRef, useState } from 'react'
import { Typography } from 'antd'
import { InboxOutlined } from '@ant-design/icons'
import { SUPPORTED_EXTENSIONS, MAX_FILE_SIZE } from '../types/knowledge'
import styles from './knowledge-panel.module.css'

const { Text } = Typography

interface DocumentUploadProps {
  /** 上传回调 */
  onUpload: (file: File) => Promise<void>
}

/**
 * 文档上传区域
 * 支持拖拽 + 点击选择，有文件类型和大小限制提示
 */
export function DocumentUpload({ onUpload }: DocumentUploadProps) {
  const [dragging, setDragging] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const validateFile = useCallback((file: File): string | null => {
    const ext = '.' + file.name.split('.').pop()?.toLowerCase()
    if (!SUPPORTED_EXTENSIONS.includes(ext)) {
      return `不支持的文件类型: ${ext}`
    }
    if (file.size > MAX_FILE_SIZE) {
      return `文件大小超过限制 (最大 ${MAX_FILE_SIZE / 1024 / 1024}MB)`
    }
    return null
  }, [])

  const processFiles = useCallback(
    async (files: FileList | File[]) => {
      for (const file of Array.from(files)) {
        const error = validateFile(file)
        if (error) {
          const { message } = await import('antd')
          message.warning(error)
          continue
        }
        await onUpload(file)
      }
    },
    [onUpload, validateFile]
  )

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragging(false)
  }, [])

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      e.stopPropagation()
      setDragging(false)
      if (e.dataTransfer.files.length > 0) {
        processFiles(e.dataTransfer.files)
      }
    },
    [processFiles]
  )

  const handleClick = useCallback(() => {
    fileInputRef.current?.click()
  }, [])

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files && e.target.files.length > 0) {
        processFiles(e.target.files)
        e.target.value = ''
      }
    },
    [processFiles]
  )

  const accept = SUPPORTED_EXTENSIONS.join(',')

  return (
    <div
      className={`${styles.uploadZone} ${dragging ? styles.uploadZoneActive : ''}`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      onClick={handleClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') handleClick()
      }}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept={accept}
        multiple
        style={{ display: 'none' }}
        onChange={handleFileChange}
      />
      <div className={styles.uploadIcon}>
        <InboxOutlined />
      </div>
      <div className={styles.uploadTitle}>点击或拖拽文件到此区域上传</div>
      <Text type="secondary" className={styles.uploadHint}>
        支持 PDF、DOCX、MD、TXT、JSON、CSV、YAML、HTML、XML、ZIP，单文件最大 20MB
      </Text>
    </div>
  )
}
