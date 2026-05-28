import React, { Component, type ErrorInfo, type ReactNode } from 'react'
import { Result, Button, Typography } from 'antd'
import { reportError } from '@/services/error-reporter'

const { Text } = Typography

interface Props {
  children: ReactNode
  moduleName: string
  onError?: (error: Error, errorInfo: ErrorInfo) => void
}

interface State {
  hasError: boolean
  error: Error | null
}

/**
 * 模块级 ErrorBoundary
 * 每个功能模块独立包裹，模块崩溃不影响其他模块
 */
export class ModuleErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error(`[ModuleErrorBoundary:${this.props.moduleName}]`, error, errorInfo)

    // 自动上报错误到后端，附带模块名
    reportError(error, errorInfo, this.props.moduleName)

    this.props.onError?.(error, errorInfo)
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null })
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: 24 }}>
          <Result
            status="warning"
            title={`${this.props.moduleName}模块加载失败`}
            subTitle={
              <Text type="secondary" style={{ fontSize: 13 }}>
                {this.state.error?.message || '未知错误'}
              </Text>
            }
            extra={
              <Button type="primary" onClick={this.handleRetry}>
                重新加载此模块
              </Button>
            }
          />
        </div>
      )
    }

    return this.props.children
  }
}
