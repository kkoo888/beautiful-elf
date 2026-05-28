/** 子代理主面板 */

import { Button, Space, Badge, Spin } from 'antd'
import { StopOutlined, ReloadOutlined } from '@ant-design/icons'
import { PageHeader } from '@/components/page-header'
import { confirmDialog } from '@/components/confirm-dialog'
import { useSubagent } from '../hooks/use-subagent'
import { SubagentList } from './subagent-list'
import { SubagentTimeline } from './subagent-timeline'
import styles from './subagent-panel.module.css'

/** 子代理面板 */
export default function SubagentPanel() {
  const {
    runs,
    isLoading,
    runningCount,
    selectedId,
    setSelectedId,
    selectedRun,
    stopRunMut,
    stopAllMut,
  } = useSubagent()

  const handleStopAll = async () => {
    const confirmed = await confirmDialog({
      title: '终止全部子代理',
      content: `确定要终止所有 ${runningCount} 个运行中的子代理吗？`,
      okText: '终止全部',
      danger: true,
    })
    if (confirmed) {
      void stopAllMut()
    }
  }

  return (
    <div className={styles.panel}>
      <PageHeader
        title="🤖 子代理"
        description="子代理运行管理"
        extra={
          <Space>
            {runningCount > 0 && (
              <Badge count={runningCount} size="small">
                <span className={styles.runningBadge}>运行中</span>
              </Badge>
            )}
            <Button
              danger
              icon={<StopOutlined />}
              onClick={handleStopAll}
              disabled={runningCount === 0}
            >
              终止全部
            </Button>
            <Button icon={<ReloadOutlined />} onClick={() => void 0}>
              刷新
            </Button>
          </Space>
        }
      />
      <SubagentList
        runs={runs}
        loading={isLoading}
        onStop={(id) => void stopRunMut(id)}
        onSelect={setSelectedId}
        selectedId={selectedId}
      />
      <SubagentTimeline run={selectedRun} />
    </div>
  )
}
