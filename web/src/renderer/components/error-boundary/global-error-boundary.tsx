import React, { Component, type ErrorInfo, type ReactNode } from 'react'
import { Result, Button } from 'antd'
import { reportError } from '@/services/error-reporter'

interface Props {
  children: ReactNode
  fallback?: ReactNode
  onError?: (error: Error, errorInfo: ErrorInfo) => void
}

interface State {
  hasError: boolean
  error: Error | null
}

/**
 * 应用级 ErrorBoundary
 * 全局兜底，捕获未处理的 React 错误并自动上报
 */
export class GlobalErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('[GlobalErrorBoundary]', error, errorInfo)

    // 自动上报错误到后端
    reportError(error, errorInfo)

    this.props.onError?.(error, errorInfo)
  }

  handleReload = () => {
    this.setState({ hasError: false, error: null })
    window.location.reload()
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback
      }

      return (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            height: '100vh',
          }}
        >
          <Result
            status="error"
            title="应用遇到了问题"
            subTitle={this.state.error?.message || '未知错误'}
            extra={[
              <Button type="primary" key="reload" onClick={this.handleReload}>
                重新加载
              </Button>,
            ]}
          />
        </div>
      )
    }

    return this.props.children
  }
}
