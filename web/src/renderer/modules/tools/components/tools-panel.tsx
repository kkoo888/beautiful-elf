/** 工具管理主面板 */

import { Button } from 'antd'
import { ReloadOutlined } from '@ant-design/icons'
import { PageHeader } from '@/components/page-header'
import { useTools } from '../hooks/use-tools'
import { ToolList } from './tool-list'
import styles from './tools-panel.module.css'

/** 工具管理面板 */
export default function ToolsPanel() {
  const { toolsWithStats, isLoading } = useTools()

  return (
    <div className={styles.panel}>
      <PageHeader
        title="🔌 工具管理"
        description="工具注册与调用统计"
        extra={
          <Button icon={<ReloadOutlined />} onClick={() => void 0}>
            刷新
          </Button>
        }
      />
      <ToolList tools={toolsWithStats} loading={isLoading} />
    </div>
  )
}
