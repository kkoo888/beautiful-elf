import { Modal } from 'antd'
import type { FilePreviewData } from '../types/file-preview'
import { TextPreview } from './text-preview'
import { CodePreview } from './code-preview'
import { ImagePreview } from './image-preview'
import { PdfPreview } from './pdf-preview'

interface FilePreviewModalProps {
  open: boolean
  onClose: () => void
  file: FilePreviewData | null
}

export function FilePreviewModal({ open, onClose, file }: FilePreviewModalProps) {
  if (!file) return null

  const renderContent = () => {
    switch (file.type) {
      case 'text':
        return <TextPreview content={file.content ?? ''} />
      case 'code':
        return <CodePreview content={file.content ?? ''} />
      case 'image':
        return <ImagePreview url={file.url ?? ''} name={file.name} />
      case 'pdf':
        return <PdfPreview name={file.name} size={file.size} />
      default:
        return <div>不支持的文件类型</div>
    }
  }

  return (
    <Modal
      title={file.name}
      open={open}
      onCancel={onClose}
      footer={null}
      width="80%"
      destroyOnClose
    >
      {renderContent()}
    </Modal>
  )
}
