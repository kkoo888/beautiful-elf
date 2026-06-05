/**
 * 登录/注册设置组件
 * 支持登录、注册、显示当前用户信息、退出登录
 */

import { useState, useEffect, useCallback } from 'react'
import { Button, Input, Form, Typography, Space, Avatar, Divider, message, Card, Tag } from 'antd'
import {
  UserOutlined,
  LockOutlined,
  LogoutOutlined,
  LoginOutlined,
  UserAddOutlined,
} from '@ant-design/icons'
import { API_BASE_URL, API_PREFIX } from '@/shared/constants'

const { Text, Title } = Typography

interface UserInfo {
  id: number
  username: string
  nickname: string
  avatar: string
  role: string
  status: number
}

interface AuthState {
  token: string | null
  user: UserInfo | null
}

const TOKEN_KEY = 'beautiful-elf:auth_token'
const USER_KEY = 'beautiful-elf:auth_user'

function loadAuth(): AuthState {
  try {
    const token = localStorage.getItem(TOKEN_KEY)
    const userStr = localStorage.getItem(USER_KEY)
    return {
      token,
      user: userStr ? JSON.parse(userStr) : null,
    }
  } catch {
    return { token: null, user: null }
  }
}

function saveAuth(token: string, user: UserInfo) {
  localStorage.setItem(TOKEN_KEY, token)
  localStorage.setItem(USER_KEY, JSON.stringify(user))
}

function clearAuth() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

export function LoginSettings() {
  const [auth, setAuth] = useState<AuthState>(loadAuth)
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [loading, setLoading] = useState(false)
  const [form] = Form.useForm()

  // 启动时尝试用 token 拉取最新用户信息
  useEffect(() => {
    if (auth.token) {
      fetch(`${API_BASE_URL}${API_PREFIX}/auth/me`, {
        headers: { Authorization: `Bearer ${auth.token}` },
      })
        .then((r) => r.json())
        .then((res) => {
          if (res.code === 0 && res.data) {
            const user = res.data as UserInfo
            saveAuth(auth.token!, user)
            setAuth({ token: auth.token, user })
          } else {
            // token 过期
            clearAuth()
            setAuth({ token: null, user: null })
          }
        })
        .catch(() => {
          // 网络错误，保留本地缓存
        })
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const handleLogin = useCallback(
    async (values: { username: string; password: string }) => {
      setLoading(true)
      try {
        const res = await fetch(`${API_BASE_URL}${API_PREFIX}/auth/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(values),
        })
        const data = await res.json()
        if (data.code === 0 && data.data) {
          const { token, user } = data.data
          saveAuth(token, user)
          setAuth({ token, user })
          message.success('登录成功')
          form.resetFields()
        } else {
          message.error(data.message || '登录失败')
        }
      } catch {
        message.error('网络错误，请检查后端服务')
      } finally {
        setLoading(false)
      }
    },
    [form]
  )

  const handleRegister = useCallback(
    async (values: { username: string; password: string; nickname?: string }) => {
      setLoading(true)
      try {
        const res = await fetch(`${API_BASE_URL}${API_PREFIX}/auth/register`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(values),
        })
        const data = await res.json()
        if (data.code === 0) {
          message.success('注册成功，请登录')
          setMode('login')
          form.resetFields()
        } else {
          message.error(data.message || '注册失败')
        }
      } catch {
        message.error('网络错误，请检查后端服务')
      } finally {
        setLoading(false)
      }
    },
    [form]
  )

  const handleLogout = useCallback(() => {
    clearAuth()
    setAuth({ token: null, user: null })
    message.info('已退出登录')
  }, [])

  // ─── 已登录：显示用户信息 ─────────────────

  if (auth.user) {
    return (
      <div style={{ maxWidth: 480 }}>
        <Card>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 16 }}>
            <Avatar
              size={64}
              src={auth.user.avatar || undefined}
              icon={!auth.user.avatar ? <UserOutlined /> : undefined}
            />
            <div>
              <Title level={5} style={{ margin: 0 }}>
                {auth.user.nickname || auth.user.username}
              </Title>
              <Text type="secondary">@{auth.user.username}</Text>
              <div style={{ marginTop: 4 }}>
                <Tag color={auth.user.role === 'admin' ? 'gold' : 'blue'}>
                  {auth.user.role === 'admin' ? '管理员' : '用户'}
                </Tag>
              </div>
            </div>
          </div>

          <Divider style={{ margin: '16px 0' }} />

          <Button
            danger
            icon={<LogoutOutlined />}
            onClick={handleLogout}
            block
          >
            退出登录
          </Button>
        </Card>
      </div>
    )
  }

  // ─── 未登录：登录/注册表单 ─────────────────

  return (
    <div style={{ maxWidth: 400 }}>
      <Space style={{ marginBottom: 24 }}>
        <Button
          type={mode === 'login' ? 'primary' : 'default'}
          icon={<LoginOutlined />}
          onClick={() => {
            setMode('login')
            form.resetFields()
          }}
        >
          登录
        </Button>
        <Button
          type={mode === 'register' ? 'primary' : 'default'}
          icon={<UserAddOutlined />}
          onClick={() => {
            setMode('register')
            form.resetFields()
          }}
        >
          注册
        </Button>
      </Space>

      <Form
        form={form}
        layout="vertical"
        onFinish={mode === 'login' ? handleLogin : handleRegister}
        autoComplete="off"
      >
        <Form.Item
          name="username"
          rules={[
            { required: true, message: '请输入用户名' },
            { min: 2, message: '用户名至少 2 个字符' },
          ]}
        >
          <Input prefix={<UserOutlined />} placeholder="用户名" size="large" />
        </Form.Item>

        {mode === 'register' && (
          <Form.Item name="nickname">
            <Input prefix={<UserOutlined />} placeholder="昵称（选填）" size="large" />
          </Form.Item>
        )}

        <Form.Item
          name="password"
          rules={[
            { required: true, message: '请输入密码' },
            { min: 4, message: '密码至少 4 个字符' },
          ]}
        >
          <Input.Password prefix={<LockOutlined />} placeholder="密码" size="large" />
        </Form.Item>

        <Form.Item>
          <Button
            type="primary"
            htmlType="submit"
            loading={loading}
            block
            size="large"
            icon={mode === 'login' ? <LoginOutlined /> : <UserAddOutlined />}
          >
            {mode === 'login' ? '登录' : '注册'}
          </Button>
        </Form.Item>
      </Form>

      <Text type="secondary" style={{ fontSize: 12 }}>
        {mode === 'login' ? '首次使用？点击上方"注册"创建账号' : '已有账号？点击上方"登录"'}
      </Text>
    </div>
  )
}
