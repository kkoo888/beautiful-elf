import { Button } from 'antd'
import { ExportOutlined } from '@ant-design/icons'

interface ExportButtonProps {
  /** 导出回调 */
  onExport: () => Promise<void>
}

/**
 * 导出按钮
 * 导出知识库为 JSON 文件
 */
export function ExportButton({ onExport }: ExportButtonProps) {
  return (
    <Button icon={<ExportOutlined />} onClick={onExport}>
      导出
    </Button>
  )
}
