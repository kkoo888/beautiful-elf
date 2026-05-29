import { Modal, Select, Typography, Space } from 'antd'
import { useState } from 'react'

interface IntentCorrectionProps {
  open: boolean
  onClose: () => void
  originalIntent?: string
  onConfirm?: (module: string) => void
}

const MODULE_OPTIONS = [
  { value: '对话', label: '对话' },
  { value: '日程', label: '日程' },
  { value: '剪贴板', label: '剪贴板' },
  { value: '代码片段', label: '代码片段' },
  { value: '知识库', label: '知识库' },
  { value: '记忆', label: '记忆' },
  { value: '翻译', label: '翻译' },
  { value: '技能', label: '技能' },
  { value: '工作流', label: '工作流' },
]

export default function IntentCorrection({
  open,
  onClose,
  originalIntent,
  onConfirm,
}: IntentCorrectionProps) {
  const [selectedModule, setSelectedModule] = useState<string>()

  const handleOk = () => {
    if (selectedModule) {
      onConfirm?.(selectedModule)
      setSelectedModule(undefined)
      onClose()
    }
  }

  return (
    <Modal
      title="意图纠正"
      open={open}
      onOk={handleOk}
      onCancel={onClose}
      okButtonProps={{ disabled: !selectedModule }}
    >
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        {originalIntent && (
          <div>
            <Typography.Text type="secondary">原始意图：</Typography.Text>
            <Typography.Paragraph strong>{originalIntent}</Typography.Paragraph>
          </div>
        )}
        <div>
          <Typography.Text>选择正确的模块：</Typography.Text>
          <Select
            style={{ width: '100%', marginTop: 8 }}
            placeholder="请选择模块"
            options={MODULE_OPTIONS}
            value={selectedModule}
            onChange={setSelectedModule}
          />
        </div>
      </Space>
    </Modal>
  )
}
