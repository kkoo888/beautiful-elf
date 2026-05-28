import { Image } from 'antd'

interface ImagePreviewProps {
  url: string
  name: string
}

export function ImagePreview({ url, name }: ImagePreviewProps) {
  return (
    <div style={{ display: 'flex', justifyContent: 'center', padding: '12px' }}>
      <Image src={url} alt={name} style={{ maxWidth: '100%', maxHeight: '70vh' }} />
    </div>
  )
}
