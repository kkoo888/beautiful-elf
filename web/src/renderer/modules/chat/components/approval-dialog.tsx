/**
 * 审批对话框 — 当 Agent 遇到高风险工具时弹出，等待用户确认
 */
import { Modal, Typography, Tag, Space, Button, Descriptions } from 'antd'
import { ExclamationCircleOutlined, CheckOutlined, CloseOutlined } from '@ant-design/icons'
import type { ApprovalRequest } from '../../types/chat'

const { Text, Paragraph } = Typography

interface ApprovalDialogProps {
  /** 审批请求 */
  request: ApprovalRequest | null
  /** 是否可见 */
  visible: boolean
  /** 确认回调 */
  onApprove: () => void
  /** 拒绝回调 */
  onReject: () => void
}

/** 工具风险等级颜色映射 */
const RISK_COLORS: Record<string, string> = {
  low: 'green',
  medium: 'orange',
  high: 'red',
}

export function ApprovalDialog({ request, visible, onApprove, onReject }: ApprovalDialogProps) {
  if (!request) return null

  return (
    <Modal
      title={
        <Space>
          <ExclamationCircleOutlined style={{ color: '#faad14', fontSize: 20 }} />
          <span>⚠️ 高风险操作确认</span>
        </Space>
      }
      open={visible}
      onCancel={onReject}
      width={520}
      footer={[
        <Button key="reject" icon={<CloseOutlined />} danger onClick={onReject}>
          拒绝执行
        </Button>,
        <Button key="approve" type="primary" icon={<CheckOutlined />} onClick={onApprove}>
          确认执行
        </Button>,
      ]}
    >
      <Paragraph>
        {request.message || `工具「${request.tool}」需要您的确认才能执行`}
      </Paragraph>

      <Descriptions column={1} size="small" bordered style={{ marginTop: 16 }}>
        <Descriptions.Item label="工具名称">
          <Tag color="blue">{request.tool}</Tag>
        </Descriptions.Item>
        {request.args && Object.keys(request.args).length > 0 && (
          <Descriptions.Item label="调用参数">
            <pre style={{
              margin: 0,
              padding: '8px 12px',
              background: '#f5f5f5',
              borderRadius: 6,
              fontSize: 12,
              maxHeight: 200,
              overflow: 'auto',
            }}>
              {JSON.stringify(request.args, null, 2)}
            </pre>
          </Descriptions.Item>
        )}
      </Descriptions>

      <Text type="secondary" style={{ display: 'block', marginTop: 12, fontSize: 12 }}>
        💡 请仔细确认工具参数是否正确，执行后无法撤回。
      </Text>
    </Modal>
  )
}
