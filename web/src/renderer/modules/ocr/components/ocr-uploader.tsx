import React, { useCallback } from 'react'
import { InboxOutlined } from '@ant-design/icons'
import { Upload, message } from 'antd'
import type { UploadFile, RcFile } from 'antd/es/upload'

const { Dragger } = Upload

interface OcrUploaderProps {
  onImageReady: (base64: string, fileName: string) => void
  disabled?: boolean
}

function fileToBase64(file: RcFile): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result as string)
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
}

const OcrUploader: React.FC<OcrUploaderProps> = ({ onImageReady, disabled }) => {
  const handleFile = useCallback(
    async (file: RcFile) => {
      const isImage = file.type.startsWith('image/')
      if (!isImage) {
        message.error('请上传图片文件')
        return false
      }
      const base64 = await fileToBase64(file)
      onImageReady(base64, file.name)
      return false // 阻止自动上传
    },
    [onImageReady],
  )

  const handlePaste = useCallback(
    async (e: React.ClipboardEvent) => {
      const items = e.clipboardData?.items
      if (!items) return
      for (const item of items) {
        if (item.type.startsWith('image/')) {
          const file = item.getAsFile() as RcFile | null
          if (file) {
            const base64 = await fileToBase64(file)
            onImageReady(base64, '粘贴图片')
          }
          break
        }
      }
    },
    [onImageReady],
  )

  return (
    <div onPaste={handlePaste} tabIndex={0}>
      <Dragger
        accept="image/*"
        showUploadList={false}
        beforeUpload={handleFile}
        disabled={disabled}
        multiple={false}
        fileList={[] as UploadFile[]}
      >
        <p className="ant-upload-drag-icon">
          <InboxOutlined />
        </p>
        <p className="ant-upload-text">点击或拖拽图片到此处</p>
        <p className="ant-upload-hint">支持 Ctrl+V 粘贴图片，支持常见图片格式</p>
      </Dragger>
    </div>
  )
}

export default OcrUploader
