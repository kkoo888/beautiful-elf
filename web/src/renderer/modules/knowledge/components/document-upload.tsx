import { useCallback, useState } from 'react'
import { Button, Modal, Upload } from 'antd'
import { UploadOutlined, InboxOutlined } from '@ant-design/icons'
import type { UploadProps } from 'antd'
import { SUPPORTED_EXTENSIONS, MAX_FILE_SIZE } from '../types/knowledge'
import styles from './knowledge-panel.module.css'

const { Dragger } = Upload

interface DocumentUploadProps {
  /** 上传回调 */
  onUpload: (file: File) => Promise<void>
}

/**
 * 文档上传按钮 + 弹窗
 * 点击按钮打开上传弹窗，弹窗内支持拖拽上传
 */
export function DocumentUpload({ onUpload }: DocumentUploadProps) {
  const [open, setOpen] = useState(false)
  const [uploading, setUploading] = useState(false)

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

  const handleUpload = useCallback(
    async (file: File) => {
      const error = validateFile(file)
      if (error) {
        const { message } = await import('antd')
        message.warning(error)
        return false
      }
      setUploading(true)
      try {
        await onUpload(file)
        setOpen(false) // 上传成功后关闭弹窗
      } finally {
        setUploading(false)
      }
      return false // 阻止 antd Upload 默认行为
    },
    [onUpload, validateFile]
  )

  const uploadProps: UploadProps = {
    name: 'file',
    multiple: true,
    beforeUpload: (file) => {
      handleUpload(file)
      return false
    },
    showUploadList: false,
    accept: SUPPORTED_EXTENSIONS.join(','),
  }

  return (
    <>
      <Button
        type="primary"
        icon={<UploadOutlined />}
        onClick={() => setOpen(true)}
      >
        上传文档
      </Button>

      <Modal
        title="上传文档"
        open={open}
        onCancel={() => setOpen(false)}
        footer={null}
        width={480}
        destroyOnClose
      >
        <Dragger {...uploadProps} className={styles.uploadDragger}>
          <p className="ant-upload-drag-icon">
            <InboxOutlined />
          </p>
          <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
          <p className="ant-upload-hint">
            支持 PDF、DOCX、MD、TXT 等格式，单文件最大 {MAX_FILE_SIZE / 1024 / 1024}MB
          </p>
        </Dragger>
      </Modal>
    </>
  )
}
