import { Typography, Space } from 'antd'
import { FilePdfOutlined } from '@ant-design/icons'

const { Text } = Typography

interface PdfPreviewProps {
  name: string
  size: number
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function PdfPreview({ name, size }: PdfPreviewProps) {
  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '300px',
      }}
    >
      <Space orientation="vertical" align="center" size="large">
        <FilePdfOutlined style={{ fontSize: '64px', color: '#e74c3c' }} />
        <Text strong style={{ fontSize: '16px' }}>
          {name}
        </Text>
        <Text type="secondary">{formatSize(size)}</Text>
        <Text type="secondary">PDF 预览暂不支持，请下载后查看</Text>
      </Space>
    </div>
  )
}
