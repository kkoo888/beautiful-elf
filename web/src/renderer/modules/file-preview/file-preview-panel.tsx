import { useState, useCallback } from 'react'
import { Upload, message } from 'antd'
import { InboxOutlined } from '@ant-design/icons'
import type { UploadFile } from 'antd'
import type { FilePreviewData } from './types/file-preview'
import { getFilePreviewType } from './utils/file-type'
import { FilePreviewModal } from './components/file-preview-modal'
import styles from './file-preview-panel.module.css'

const { Dragger } = Upload

export function FilePreviewPanel() {
  const [previewFile, setPreviewFile] = useState<FilePreviewData | null>(null)
  const [modalOpen, setModalOpen] = useState(false)

  const handleFile = useCallback((file: File) => {
    const fileType = getFilePreviewType(file.name)
    const baseData: Omit<FilePreviewData, 'content' | 'url'> = {
      name: file.name,
      type: fileType,
      size: file.size,
    }

    if (fileType === 'image') {
      const url = URL.createObjectURL(file)
      setPreviewFile({ ...baseData, url })
      setModalOpen(true)
      return false
    }

    if (fileType === 'text' || fileType === 'code') {
      const reader = new FileReader()
      reader.onload = (e) => {
        const content = (e.target?.result as string) ?? ''
        setPreviewFile({ ...baseData, content })
        setModalOpen(true)
      }
      reader.readAsText(file)
      return false
    }

    if (fileType === 'pdf') {
      setPreviewFile(baseData)
      setModalOpen(true)
      return false
    }

    message.warning('不支持的文件类型')
    return false
  }, [])

  const handleClose = useCallback(() => {
    setModalOpen(false)
    if (previewFile?.url) {
      URL.revokeObjectURL(previewFile.url)
    }
    setPreviewFile(null)
  }, [previewFile])

  return (
    <div className={styles.panel}>
      <h2 className={styles.title}>文件预览</h2>
      <Dragger
        beforeUpload={handleFile}
        showUploadList={false}
        multiple={false}
        accept=".txt,.md,.json,.yaml,.yml,.js,.ts,.py,.html,.css,.jsx,.tsx,.java,.go,.rs,.vue,.jpg,.jpeg,.png,.gif,.webp,.svg,.pdf"
      >
        <p className="ant-upload-drag-icon">
          <InboxOutlined />
        </p>
        <p className="ant-upload-text">点击或拖拽文件到此区域进行预览</p>
        <p className="ant-upload-hint">
          支持文本、代码、图片、PDF 等常见文件格式
        </p>
      </Dragger>
      <FilePreviewModal open={modalOpen} onClose={handleClose} file={previewFile} />
    </div>
  )
}
