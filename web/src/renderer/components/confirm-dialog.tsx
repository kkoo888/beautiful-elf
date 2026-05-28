import { Modal, Typography } from 'antd'
import { ExclamationCircleOutlined } from '@ant-design/icons'
import type { ReactNode } from 'react'

const { Text } = Typography

interface ConfirmDialogOptions {
  /** 标题 */
  title: string
  /** 内容描述 */
  content: ReactNode
  /** 确认按钮文字 */
  okText?: string
  /** 取消按钮文字 */
  cancelText?: string
  /** 确认按钮类型 */
  okType?: 'primary' | 'default' | 'dashed' | 'link' | 'text'
  /** 是否为危险操作（红色确认按钮） */
  danger?: boolean
}

/**
 * 确认对话框
 * 封装 Modal.confirm，统一风格
 */
export function confirmDialog({
  title,
  content,
  okText = '确认',
  cancelText = '取消',
  okType = 'primary',
  danger = false
}: ConfirmDialogOptions): Promise<boolean> {
  return new Promise((resolve) => {
    Modal.confirm({
      title,
      icon: danger ? <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} /> : undefined,
      content: typeof content === 'string' ? <Text>{content}</Text> : content,
      okText,
      cancelText,
      okType: danger ? 'primary' : okType,
      okButtonProps: danger ? { danger: true } : undefined,
      onOk: () => resolve(true),
      onCancel: () => resolve(false)
    })
  })
}

/**
 * 危险操作确认对话框（红色确认按钮）
 */
export function confirmDanger(title: string, content: ReactNode): Promise<boolean> {
  return confirmDialog({ title, content, danger: true, okText: '确认删除' })
}
