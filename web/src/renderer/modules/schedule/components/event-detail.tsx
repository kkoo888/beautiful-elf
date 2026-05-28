/** 日程详情弹窗 */

import { memo } from 'react'
import { Modal, Button, Space, Popconfirm, Tag } from 'antd'
import {
  EditOutlined,
  DeleteOutlined,
  ClockCircleOutlined,
  CalendarOutlined,
  BellOutlined,
  ReloadOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'
import type { Schedule } from '@/types'
import { ReminderBadge } from './reminder-badge'
import styles from './schedule-panel.module.css'

const REPEAT_LABELS: Record<string, string> = {
  none: '不重复',
  daily: '每天',
  weekly: '每周',
  monthly: '每月',
}

interface EventDetailProps {
  open: boolean
  event: Schedule | null
  onClose: () => void
  onEdit: (event: Schedule) => void
  onDelete: (id: string) => void
}

export const EventDetail = memo<EventDetailProps>(function EventDetail({
  open,
  event,
  onClose,
  onEdit,
  onDelete,
}) {
  if (!event) return null

  const startTime = dayjs(event.start_time)
  const endTime = dayjs(event.end_time)
  const isSameDay = startTime.isSame(endTime, 'day')

  const handleDelete = () => {
    onDelete(event.id)
    onClose()
  }

  return (
    <Modal
      open={open}
      onCancel={onClose}
      title={
        <Space>
          <span
            style={{
              display: 'inline-block',
              width: 12,
              height: 12,
              borderRadius: '50%',
              backgroundColor: event.color || '#f97316',
            }}
          />
          {event.title}
        </Space>
      }
      footer={
        <Space>
          <Popconfirm
            title="确定删除此日程？"
            onConfirm={handleDelete}
            okText="删除"
            cancelText="取消"
            okButtonProps={{ danger: true }}
          >
            <Button danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
          <Button
            type="primary"
            icon={<EditOutlined />}
            onClick={() => onEdit(event)}
          >
            编辑
          </Button>
        </Space>
      }
      width={480}
    >
      <div className={styles.detailContent}>
        {/* 时间 */}
        <div className={styles.detailRow}>
          <span className={styles.detailLabel}>
            <ClockCircleOutlined /> 时间
          </span>
          <span className={styles.detailValue}>
            {event.is_all_day ? (
              isSameDay ? (
                `${startTime.format('YYYY-MM-DD')} 全天`
              ) : (
                `${startTime.format('YYYY-MM-DD')} - ${endTime.format('YYYY-MM-DD')} 全天`
              )
            ) : isSameDay ? (
              `${startTime.format('YYYY-MM-DD HH:mm')} - ${endTime.format('HH:mm')}`
            ) : (
              `${startTime.format('YYYY-MM-DD HH:mm')} - ${endTime.format('YYYY-MM-DD HH:mm')}`
            )}
          </span>
        </div>

        {/* 提醒 */}
        {event.reminder_minutes > 0 && (
          <div className={styles.detailRow}>
            <span className={styles.detailLabel}>
              <BellOutlined /> 提醒
            </span>
            <span className={styles.detailValue}>
              <ReminderBadge minutes={event.reminder_minutes} />
            </span>
          </div>
        )}

        {/* 重复 */}
        {event.repeat && event.repeat !== 'none' && (
          <div className={styles.detailRow}>
            <span className={styles.detailLabel}>
              <ReloadOutlined /> 重复
            </span>
            <span className={styles.detailValue}>
              <Tag>{REPEAT_LABELS[event.repeat] ?? event.repeat}</Tag>
            </span>
          </div>
        )}

        {/* 颜色 */}
        <div className={styles.detailRow}>
          <span className={styles.detailLabel}>标签</span>
          <span className={styles.detailValue}>
            <Tag color={event.color || '#f97316'}>{event.color || '默认'}</Tag>
          </span>
        </div>

        {/* 描述 */}
        {event.description && (
          <div className={styles.detailRow}>
            <span className={styles.detailLabel}>描述</span>
            <div className={styles.detailDesc}>{event.description}</div>
          </div>
        )}

        {/* 创建/更新时间 */}
        <div className={styles.detailRow}>
          <span className={styles.detailLabel}>
            <CalendarOutlined /> 创建
          </span>
          <span className={styles.detailValue} style={{ fontSize: 12, color: 'var(--color-text-secondary, #999)' }}>
            {dayjs(event.created_at).format('YYYY-MM-DD HH:mm')}
          </span>
        </div>
      </div>
    </Modal>
  )
})
