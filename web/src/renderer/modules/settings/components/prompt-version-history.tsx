/**
 * Prompt 版本历史弹窗
 * Timeline 展示版本列表，支持设为激活和打开 diff 对比
 */

import { useState } from 'react'
import { Modal, Timeline, Tag, Button, Space, Typography } from 'antd'
import { CheckCircleFilled, SwapOutlined, RocketOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import type { PromptConfig } from '../types/settings'
import { PromptDiff } from './prompt-diff'

const { Text, Paragraph } = Typography

interface PromptVersionHistoryProps {
  /** 当前 Prompt 配置 */
  prompt: PromptConfig
  /** 弹窗是否可见 */
  open: boolean
  /** 关闭回调 */
  onClose: () => void
  /** 设为激活版本 */
  onSetActive: (versionId: string) => void
}

export function PromptVersionHistory({
  prompt,
  open,
  onClose,
  onSetActive,
}: PromptVersionHistoryProps) {
  const [diffOpen, setDiffOpen] = useState(false)
  const [diffVersions, setDiffVersions] = useState<{
    leftId: string
    rightId: string
  } | null>(null)

  const sortedVersions = [...prompt.versions].sort((a, b) => b.version - a.version)

  const handleOpenDiff = (leftId: string, rightId: string) => {
    setDiffVersions({ leftId, rightId })
    setDiffOpen(true)
  }

  return (
    <>
      <Modal
        title={`版本历史 — ${prompt.name}`}
        open={open}
        onCancel={onClose}
        footer={null}
        width={640}
        destroyOnHidden
      >
        <Timeline
          items={sortedVersions.map((version) => ({
            color: version.isActive ? 'green' : 'gray',
            children: (
              <div key={version.id}>
                <Space align="center" style={{ marginBottom: 8 }}>
                  <Text strong>v{version.version}</Text>
                  {version.isActive && (
                    <Tag color="green" icon={<CheckCircleFilled />}>
                      当前激活
                    </Tag>
                  )}
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {dayjs(version.createdAt).format('YYYY-MM-DD HH:mm')}
                  </Text>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    by {version.createdBy}
                  </Text>
                </Space>

                <Paragraph
                  ellipsis={{ rows: 3, expandable: true, symbol: '展开' }}
                  style={{
                    marginBottom: 8,
                    padding: '8px 12px',
                    background: '#fafafa',
                    borderRadius: 6,
                    fontSize: 13,
                    whiteSpace: 'pre-wrap',
                  }}
                >
                  {version.content || '（空内容）'}
                </Paragraph>

                <Space size="small">
                  {!version.isActive && (
                    <Button
                      type="link"
                      size="small"
                      icon={<RocketOutlined />}
                      onClick={() => onSetActive(version.id)}
                    >
                      设为激活
                    </Button>
                  )}
                  {/* 与上一版本对比 */}
                  {version !== sortedVersions[sortedVersions.length - 1] && (
                    <Button
                      type="link"
                      size="small"
                      icon={<SwapOutlined />}
                      onClick={() => {
                        const idx = sortedVersions.indexOf(version)
                        const older = sortedVersions[idx + 1]
                        handleOpenDiff(older.id, version.id)
                      }}
                    >
                      与上一版本对比
                    </Button>
                  )}
                </Space>
              </div>
            ),
          }))}
        />
      </Modal>

      {/* Diff 弹窗 */}
      {diffVersions && (
        <PromptDiff
          versions={prompt.versions}
          leftId={diffVersions.leftId}
          rightId={diffVersions.rightId}
          open={diffOpen}
          onClose={() => {
            setDiffOpen(false)
            setDiffVersions(null)
          }}
        />
      )}
    </>
  )
}
