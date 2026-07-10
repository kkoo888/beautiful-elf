/**
 * 基本信息设置 — 管理应用背景图
 * 存储：path 存入 setting 表（key=branding.background_image），图片存 uploads/branding/
 */
import { useState, useEffect, useCallback } from 'react'
import { Upload, Button, Typography, Card, Image, Space, Divider, App } from 'antd'
import { UploadOutlined, DeleteOutlined, PictureOutlined, ReloadOutlined } from '@ant-design/icons'
import { apiClient, extractData } from '@/services/api-client'

const { Text, Title } = Typography

const CONFIG_KEY = 'branding.background_image'

export function BasicInfoSettings() {
  const [bgPath, setBgPath] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const [previewUrl, setPreviewUrl] = useState<string>('')
  const { message } = App.useApp()

  // 加载背景图路径（从 setting 表）
  const loadBg = useCallback(() => {
    apiClient
      .get(`/configs/${CONFIG_KEY}`)
      .then((res) => {
        const data = extractData(res) as { keyValue?: string }
        if (data?.keyValue) {
          setBgPath(data.keyValue)
          setPreviewUrl(`${window.location.origin}/${data.keyValue}`)
        } else {
          setBgPath('')
          setPreviewUrl('')
        }
      })
      .catch(() => {
        setBgPath('')
        setPreviewUrl('')
      })
  }, [])

  useEffect(() => { loadBg() }, [loadBg])

  // 上传背景图
  const handleUpload = useCallback(async (file: File) => {
    if (!file.type.startsWith('image/')) {
      message.error('请上传图片文件（JPG/PNG/WebP）')
      return false
    }
    if (file.size > 5 * 1024 * 1024) {
      message.error('图片大小不能超过 5MB')
      return false
    }

    setLoading(true)
    try {
      // 1. 上传文件
      const formData = new FormData()
      formData.append('file', file)
      const uploadRes = await apiClient.post('/branding/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      const uploadData = extractData(uploadRes) as { path?: string }
      if (!uploadData?.path) {
        message.error('上传失败')
        return false
      }

      // 2. 存路径到 setting 表
      try {
        await apiClient.put(`/configs/${CONFIG_KEY}`, {
          keyValue: uploadData.path,
          description: '应用背景图片路径',
        })
      } catch {
        await apiClient.post('/configs', {
          settingsKey: CONFIG_KEY,
          keyValue: uploadData.path,
          description: '应用背景图片路径',
        })
      }

      setBgPath(uploadData.path)
      setPreviewUrl(`${window.location.origin}/${uploadData.path}`)
      message.success('背景图已更新')
    } catch {
      message.error('上传失败')
    } finally {
      setLoading(false)
    }
    return false
  }, [message])

  // 删除背景图
  const handleDelete = useCallback(async () => {
    setLoading(true)
    try {
      await apiClient.delete(`/configs/${CONFIG_KEY}`)
      setBgPath('')
      setPreviewUrl('')
      message.success('背景图已删除')
    } catch {
      message.error('删除失败')
    } finally {
      setLoading(false)
    }
  }, [message])

  return (
    <div style={{ maxWidth: 520 }}>
      <Card
        title={
          <Space>
            <PictureOutlined />
            <span>应用背景图</span>
          </Space>
        }
        extra={
          <Button
            type="text"
            icon={<ReloadOutlined />}
            onClick={loadBg}
            size="small"
          >
            刷新
          </Button>
        }
        styles={{ body: { padding: '16px 24px' } }}
      >
        <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
          设置应用的背景图片，会显示在聊天面板等位置。
          <br />
          支持 JPG、PNG、WebP 格式，最大 5MB。
        </Text>

        <Divider style={{ margin: '12px 0' }} />

        {/* 预览区 */}
        {previewUrl ? (
          <div style={{ marginBottom: 16 }}>
            <Text type="secondary" style={{ fontSize: 12, marginBottom: 8, display: 'block' }}>
              预览
            </Text>
            <div
              style={{
                borderRadius: 8,
                overflow: 'hidden',
                border: '1px solid #f0f0f0',
                background: '#fafafa',
              }}
            >
              <Image
                src={previewUrl}
                alt="背景图预览"
                style={{ width: '100%', maxHeight: 200, objectFit: 'cover', display: 'block' }}
                fallback="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
                preview={{ mask: <div style={{ fontSize: 14 }}>点击预览</div> }}
              />
            </div>
          </div>
        ) : (
          <div
            style={{
              marginBottom: 16,
              padding: '32px 0',
              background: 'linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)',
              borderRadius: 8,
              textAlign: 'center',
              border: '1px dashed #d9d9d9',
            }}
          >
            <PictureOutlined style={{ fontSize: 40, color: '#bfbfbf' }} />
            <div style={{ marginTop: 8, color: '#999', fontSize: 13 }}>
              暂未设置背景图
            </div>
            <div style={{ marginTop: 4, color: '#bbb', fontSize: 12 }}>
              上传后将显示在聊天面板背景
            </div>
          </div>
        )}

        {/* 操作按钮 */}
        <Space>
          <Upload showUploadList={false} beforeUpload={handleUpload} accept="image/*">
            <Button
              type="primary"
              icon={<UploadOutlined />}
              loading={loading}
            >
              {bgPath ? '更换背景图' : '上传背景图'}
            </Button>
          </Upload>

          {bgPath && (
            <Button
              danger
              icon={<DeleteOutlined />}
              onClick={handleDelete}
              loading={loading}
            >
              删除背景图
            </Button>
          )}
        </Space>

        {/* 当前路径 */}
        {bgPath && (
          <div style={{ marginTop: 12, padding: '8px 12px', background: '#f6f6f6', borderRadius: 6 }}>
            <Text type="secondary" style={{ fontSize: 12 }}>
              📁 存储路径: <code style={{ background: '#fff', padding: '1px 4px', borderRadius: 3 }}>{bgPath}</code>
            </Text>
          </div>
        )}
      </Card>
    </div>
  )
}
