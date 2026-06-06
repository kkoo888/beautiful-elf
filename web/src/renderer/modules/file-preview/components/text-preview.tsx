import { Typography } from 'antd'

const { Paragraph } = Typography

interface TextPreviewProps {
  content: string
}

export function TextPreview({ content }: TextPreviewProps) {
  return (
    <div style={{ maxHeight: '70vh', overflow: 'auto', padding: '12px' }}>
      <Paragraph style={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace' }}>{content}</Paragraph>
    </div>
  )
}
