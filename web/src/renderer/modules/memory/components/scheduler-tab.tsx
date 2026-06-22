/** 定时任务控制 Tab — 启停记忆模块的后台定时任务 */

import { useState, useCallback, useEffect } from 'react'
import { Typography, Switch, Space, Spin, App, Tag, Descriptions } from 'antd'
import { ClockCircleOutlined } from '@ant-design/icons'
import {
  fetchSchedulerTasks, toggleSchedulerTask,
} from '../services/memory-api'
import type { SchedulerTask } from '../services/memory-api'

const { Text } = Typography

export function SchedulerTab() {
  const { message } = App.useApp()
  const [tasks, setTasks] = useState<SchedulerTask[]>([])
  const [loading, setLoading] = useState(true)
  const [toggling, setToggling] = useState<string | null>(null)

  const loadTasks = useCallback(async () => {
    try {
      const data = await fetchSchedulerTasks()
      setTasks(data)
    } catch {
      message.error('加载定时任务状态失败')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadTasks() }, [loadTasks])

  const handleToggle = useCallback(async (task: SchedulerTask, checked: boolean) => {
    setToggling(task.name)
    try {
      await toggleSchedulerTask(task.name, checked)
      setTasks(prev => prev.map(t =>
        t.name === task.name ? { ...t, enabled: checked } : t
      ))
      message.success(`${task.label} 已${checked ? '启用' : '停止'}`)
    } catch {
      message.error('操作失败')
    } finally {
      setToggling(null)
    }
  }, [])

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', paddingTop: 80 }}>
        <Spin />
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16, padding: '8px 0' }}>
      <Text type="secondary">
        控制记忆模块的后台定时任务。开关状态实时持久化，重启后保持当前设置。
      </Text>

      {tasks.map(task => (
        <div
          key={task.name}
          style={{
            padding: '16px 20px',
            borderRadius: 12,
            background: task.enabled
              ? 'linear-gradient(135deg, rgba(255,247,237,0.6) 0%, rgba(255,241,224,0.4) 100%)'
              : '#fafafa',
            border: `1px solid ${task.enabled ? 'rgba(232,145,58,0.2)' : '#f0f0f0'}`,
            transition: 'all 0.3s',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
            <Space>
              <ClockCircleOutlined style={{ color: task.enabled ? '#e8913a' : '#bfbfbf' }} />
              <Text strong style={{ fontSize: 14 }}>{task.label}</Text>
              <Tag color={task.enabled ? 'orange' : 'default'}>
                {task.enabled ? '运行中' : '已停止'}
              </Tag>
            </Space>
            <Switch
              checked={task.enabled}
              loading={toggling === task.name}
              onChange={(checked) => handleToggle(task, checked)}
            />
          </div>

          <Descriptions size="small" column={2} colon={false}>
            <Descriptions.Item label="执行间隔">
              <Text type="secondary">{task.intervalLabel}</Text>
            </Descriptions.Item>
            <Descriptions.Item label="任务标识">
              <Text code style={{ fontSize: 12 }}>{task.name}</Text>
            </Descriptions.Item>
          </Descriptions>
        </div>
      ))}
    </div>
  )
}
