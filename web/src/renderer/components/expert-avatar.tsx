/** 公共头像组件 — 统一处理 emoji 和 base64 图片头像 */

import { UserOutlined } from '@ant-design/icons'

interface ExpertAvatarProps {
  /** 头像值：emoji 字符串 或 base64 data URI */
  avatar?: string | null
  /** 尺寸（px），默认 32 */
  size?: number
  /** 背景色（emoji 模式下使用） */
  bgColor?: string
  /** 文字颜色（emoji 模式下使用） */
  color?: string
  /** 额外 class */
  className?: string
  /** 额外 style */
  style?: React.CSSProperties
}

function isImageAvatar(avatar?: string | null): boolean {
  return !!avatar && (avatar.startsWith('data:image') || avatar.startsWith('http'))
}

export function ExpertAvatar({
  avatar,
  size = 32,
  bgColor = '#e6f7ff',
  color = '#1890ff',
  className,
  style,
}: ExpertAvatarProps) {
  const isImg = isImageAvatar(avatar)

  return (
    <div
      className={className}
      style={{
        width: size,
        height: size,
        borderRadius: '50%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: size * 0.5,
        backgroundColor: isImg ? 'transparent' : bgColor,
        color: isImg ? 'transparent' : color,
        overflow: 'hidden',
        flexShrink: 0,
        ...style,
      }}
    >
      {isImg ? (
        <img
          src={avatar!}
          style={{ width: '100%', height: '100%', objectFit: 'cover' }}
          alt="avatar"
        />
      ) : (
        <UserOutlined style={{ fontSize: size * 0.45 }} />
      )}
    </div>
  )
}
