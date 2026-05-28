/** 创建/编辑日程表单（Drawer 侧滑面板） */

import { useEffect, memo } from 'react'
import { Drawer, Form, Input, DatePicker, Switch, Select, Button, Space, message } from 'antd'
import { useForm, Controller } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import dayjs from 'dayjs'
import type { Schedule } from '@/types'
import type { ScheduleFormInput } from '../types/schedule'
import { SCHEDULE_COLORS, REMINDER_OPTIONS } from '../types/schedule'
import styles from './schedule-panel.module.css'

const { TextArea } = Input
const { RangePicker } = DatePicker

// Zod Schema
const scheduleSchema = z
  .object({
    title: z.string().min(1, '标题不能为空').max(100, '标题最多 100 个字符'),
    description: z.string().max(500, '描述最多 500 个字符').optional(),
    timeRange: z
      .tuple([
        z.instanceof(dayjs as unknown as typeof dayjs),
        z.instanceof(dayjs as unknown as typeof dayjs),
      ])
      .refine((val) => val[0].isValid() && val[1].isValid(), '请选择有效的时间范围'),
    isAllDay: z.boolean(),
    reminderMinutes: z.number().min(0).max(1440),
    color: z.string().optional(),
    repeat: z.enum(['none', 'daily', 'weekly', 'monthly']),
  })
  .refine((data) => data.timeRange[1].isAfter(data.timeRange[0]), {
    message: '结束时间必须晚于开始时间',
    path: ['timeRange'],
  })

type FormData = z.infer<typeof scheduleSchema>

interface EventFormProps {
  open: boolean
  onClose: () => void
  onSubmit: (data: ScheduleFormInput) => Promise<void>
  /** 编辑模式时传入已有日程 */
  editingEvent?: Schedule | null
  /** 点击日期创建时的初始日期 */
  initialDate?: dayjs.Dayjs
}

export const EventForm = memo<EventFormProps>(function EventForm({
  open,
  onClose,
  onSubmit,
  editingEvent,
  initialDate,
}) {
  const {
    control,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(scheduleSchema),
    defaultValues: {
      title: '',
      description: '',
      timeRange: [dayjs(), dayjs().add(1, 'hour')],
      isAllDay: false,
      reminderMinutes: 15,
      color: SCHEDULE_COLORS[0].value,
      repeat: 'none',
    },
  })

  // 编辑模式 / 创建模式初始化
  useEffect(() => {
    if (!open) return

    if (editingEvent) {
      reset({
        title: editingEvent.title,
        description: editingEvent.description || '',
        timeRange: [dayjs(editingEvent.start_time), dayjs(editingEvent.end_time)],
        isAllDay: editingEvent.is_all_day,
        reminderMinutes: editingEvent.reminder_minutes,
        color: editingEvent.color || SCHEDULE_COLORS[0].value,
        repeat: editingEvent.repeat as 'none' | 'daily' | 'weekly' | 'monthly',
      })
    } else {
      const start = initialDate ?? dayjs()
      reset({
        title: '',
        description: '',
        timeRange: [start.startOf('hour'), start.startOf('hour').add(1, 'hour')],
        isAllDay: false,
        reminderMinutes: 15,
        color: SCHEDULE_COLORS[0].value,
        repeat: 'none',
      })
    }
  }, [open, editingEvent, initialDate, reset])

  const handleFormSubmit = async (data: FormData) => {
    try {
      const input: ScheduleFormInput = {
        title: data.title,
        description: data.description || undefined,
        startTime: data.timeRange[0].toDate(),
        endTime: data.timeRange[1].toDate(),
        isAllDay: data.isAllDay,
        reminderMinutes: data.reminderMinutes,
        color: data.color,
        repeat: data.repeat,
      }
      await onSubmit(input)
      message.success(editingEvent ? '日程已更新' : '日程已创建')
      onClose()
    } catch {
      message.error('操作失败，请重试')
    }
  }

  return (
    <Drawer
      title={editingEvent ? '编辑日程' : '新建日程'}
      open={open}
      onClose={onClose}
      width={420}
      destroyOnClose
      footer={
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
          <Button onClick={onClose}>取消</Button>
          <Button
            type="primary"
            loading={isSubmitting}
            onClick={() => void handleSubmit(handleFormSubmit)()}
          >
            {editingEvent ? '保存' : '创建'}
          </Button>
        </div>
      }
    >
      <Form layout="vertical" autoComplete="off">
        {/* 标题 */}
        <Form.Item
          label="标题"
          required
          validateStatus={errors.title ? 'error' : undefined}
          help={errors.title?.message}
        >
          <Controller
            name="title"
            control={control}
            render={({ field }) => <Input {...field} placeholder="输入日程标题" maxLength={100} />}
          />
        </Form.Item>

        {/* 时间范围 */}
        <Form.Item
          label="时间"
          required
          validateStatus={errors.timeRange ? 'error' : undefined}
          help={errors.timeRange?.message}
        >
          <Controller
            name="timeRange"
            control={control}
            render={({ field }) => (
              <Controller
                name="isAllDay"
                control={control}
                render={({ field: allDayField }) => (
                  <RangePicker
                    value={field.value as [dayjs.Dayjs, dayjs.Dayjs]}
                    onChange={(val) => {
                      if (val && val[0] && val[1]) {
                        field.onChange(val)
                      }
                    }}
                    showTime={!allDayField.value ? { format: 'HH:mm' } : false}
                    format={allDayField.value ? 'YYYY-MM-DD' : 'YYYY-MM-DD HH:mm'}
                    style={{ width: '100%' }}
                    placeholder={['开始时间', '结束时间']}
                  />
                )}
              />
            )}
          />
        </Form.Item>

        {/* 全天事件 */}
        <Form.Item label="全天事件">
          <Controller
            name="isAllDay"
            control={control}
            render={({ field }) => <Switch checked={field.value} onChange={field.onChange} />}
          />
        </Form.Item>

        {/* 描述 */}
        <Form.Item
          label="描述"
          validateStatus={errors.description ? 'error' : undefined}
          help={errors.description?.message}
        >
          <Controller
            name="description"
            control={control}
            render={({ field }) => (
              <TextArea
                {...field}
                placeholder="添加描述（可选）"
                rows={3}
                maxLength={500}
                showCount
              />
            )}
          />
        </Form.Item>

        {/* 提前提醒 */}
        <Form.Item label="提前提醒">
          <Controller
            name="reminderMinutes"
            control={control}
            render={({ field }) => (
              <Select
                value={field.value}
                onChange={field.onChange}
                options={REMINDER_OPTIONS.map((o) => ({
                  label: o.label,
                  value: o.value,
                }))}
              />
            )}
          />
        </Form.Item>

        {/* 颜色 */}
        <Form.Item label="颜色标签">
          <Controller
            name="color"
            control={control}
            render={({ field }) => (
              <div className={styles.colorPicker}>
                {SCHEDULE_COLORS.map((c) => (
                  <div
                    key={c.value}
                    className={`${styles.colorDot} ${field.value === c.value ? styles.selected : ''}`}
                    style={{ backgroundColor: c.value }}
                    onClick={() => field.onChange(c.value)}
                    title={c.label}
                  />
                ))}
              </div>
            )}
          />
        </Form.Item>

        {/* 重复 */}
        <Form.Item label="重复">
          <Controller
            name="repeat"
            control={control}
            render={({ field }) => (
              <Select
                value={field.value}
                onChange={field.onChange}
                options={[
                  { label: '不重复', value: 'none' },
                  { label: '每天', value: 'daily' },
                  { label: '每周', value: 'weekly' },
                  { label: '每月', value: 'monthly' },
                ]}
              />
            )}
          />
        </Form.Item>
      </Form>
    </Drawer>
  )
})
