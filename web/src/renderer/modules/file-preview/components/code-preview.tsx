import CodeMirror from '@uiw/react-codemirror'
import { oneDark } from '@codemirror/theme-one-dark'

interface CodePreviewProps {
  content: string
  language?: string
}

export function CodePreview({ content, language }: CodePreviewProps) {
  return (
    <div style={{ maxHeight: '70vh', overflow: 'auto' }}>
      <CodeMirror value={content} theme={oneDark} editable={false} style={{ fontSize: '14px' }} />
    </div>
  )
}
