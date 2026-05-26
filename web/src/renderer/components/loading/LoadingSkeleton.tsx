import { Skeleton, Spin } from 'antd'

interface LoadingSkeletonProps {
  rows?: number
  type?: 'text' | 'card' | 'table'
}

export function LoadingSkeleton({ rows = 3, type = 'text' }: LoadingSkeletonProps) {
  if (type === 'card') {
    return (
      <div style={{ padding: 16 }}>
        <Skeleton active avatar paragraph={{ rows: 2 }} />
      </div>
    )
  }

  if (type === 'table') {
    return (
      <div style={{ padding: 16 }}>
        <Skeleton active paragraph={{ rows: 8 }} />
      </div>
    )
  }

  return <Skeleton active paragraph={{ rows }} />
}

interface LoadingSpinProps {
  tip?: string
  children?: React.ReactNode
}

export function LoadingSpin({ tip = '加载中...', children }: LoadingSpinProps) {
  return (
    <Spin tip={tip} size="small">
      {children}
    </Spin>
  )
}
