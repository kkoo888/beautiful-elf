/**
 * 工具审批弹窗 — 从输入框底部滑出的紧凑型确认面板
 *
 * 设计参考 Claude Code + Cursor：
 *   - 三档：拒绝 / 允许本次 / 添加白名单
 *   - 命令预览（exec_command）/ Diff 预览（write_file）
 *   - 风险等级标签
 *   - 超出工作区警告
 *   - 90秒超时自动拒绝
 */
import React, { useEffect, useState, useCallback } from 'react'
import { Button, Tag, Tooltip, message as antMessage } from 'antd'
import {
  CloseOutlined,
  CheckOutlined,
  SafetyOutlined,
  WarningOutlined,
  CodeOutlined,
  FileOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons'
import type { ApprovalRequest, RiskLevel } from '../types/chat'
import styles from './approval-popup.module.css'

interface ApprovalPopupProps {
  /** 审批请求 */
  request: ApprovalRequest | null
  /** 是否可见 */
  visible: boolean
  /** 允许本次回调 */
  onApprove: () => void
  /** 拒绝回调 */
  onReject: () => void
  /** 添加白名单回调 */
  onWhitelist: (pathPattern: string, commandPattern: string) => void
}

/** 风险等级配置 */
const RISK_CONFIG: Record<RiskLevel, { color: string; label: string; icon: React.ReactNode }> = {
  low: { color: 'green', label: '低风险', icon: <SafetyOutlined /> },
  medium: { color: 'orange', label: '中风险', icon: <WarningOutlined /> },
  high: { color: 'red', label: '高风险', icon: <WarningOutlined /> },
}

/** 超时秒数 */
const TIMEOUT_SECONDS = 90

export const ApprovalPopup: React.FC<ApprovalPopupProps> = ({
  request,
  visible,
  onApprove,
  onReject,
  onWhitelist,
}) => {
  const [countdown, setCountdown] = useState(TIMEOUT_SECONDS)
  const [showWhitelistForm, setShowWhitelistForm] = useState(false)

  // 重置倒计时
  useEffect(() => {
    if (!visible) {
      setCountdown(TIMEOUT_SECONDS)
      setShowWhitelistForm(false)
      return
    }
    setCountdown(TIMEOUT_SECONDS)
    const timer = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(timer)
          antMessage.warning('审批超时，已自动拒绝')
          onReject()
          return 0
        }
        return prev - 1
      })
    }, 1000)
    return () => clearInterval(timer)
  }, [visible, onReject])

  // 快捷键
  useEffect(() => {
    if (!visible) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onReject()
      if (e.key === 'Enter' && !showWhitelistForm) onApprove()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [visible, showWhitelistForm, onApprove, onReject])

  if (!request || !visible) return null

  const risk = request.riskLevel || 'medium'
  const riskConfig = RISK_CONFIG[risk]
  const isCommand = request.tool === 'exec_command'
  const isWrite = ['write_file', 'apply_patch'].includes(request.tool)

  // 提取路径和命令用于白名单
  const extractPath = (): string => {
    if (isCommand) return request.workingDirectory || ''
    return (request.args?.path as string) || (request.args?.workdir as string) || ''
  }
  const extractCommand = (): string => {
    if (isCommand) return (request.args?.command as string) || ''
    return ''
  }

  return (
    <div className={styles.overlay}>
      <div className={styles.popup}>
        {/* 头部：风险等级 + 倒计时 */}
        <div className={styles.header}>
          <div className={styles.headerLeft}>
            <Tag color={riskConfig.color} icon={riskConfig.icon}>
              {riskConfig.label}
            </Tag>
            <span className={styles.toolName}>
              {isCommand ? <CodeOutlined /> : <FileOutlined />}
              {request.tool}
            </span>
          </div>
          <div className={styles.countdown}>
            <ClockCircleOutlined />
            <span className={countdown <= 10 ? styles.countdownDanger : ''}>
              {countdown}s
            </span>
          </div>
        </div>

        {/* 超出工作区警告 */}
        {request.outsideWorkspace && (
          <div className={styles.workspaceWarning}>
            <WarningOutlined /> 工作区外的操作 — 请谨慎确认
          </div>
        )}

        {/* 命令预览 */}
        {isCommand && request.commandPreview && (
          <div className={styles.preview}>
            <div className={styles.previewLabel}>命令</div>
            <pre className={styles.commandBlock}>
              <code>$ {request.commandPreview}</code>
            </pre>
          </div>
        )}

        {/* Diff 预览 */}
        {isWrite && request.diffPreview && (
          <div className={styles.preview}>
            <div className={styles.previewLabel}>变更</div>
            <pre className={styles.diffBlock}>
              <code>{request.diffPreview}</code>
            </pre>
          </div>
        )}

        {/* 参数预览（兜底） */}
        {!request.commandPreview && !request.diffPreview && Object.keys(request.args).length > 0 && (
          <div className={styles.preview}>
            <div className={styles.previewLabel}>参数</div>
            <pre className={styles.argsBlock}>
              <code>{JSON.stringify(request.args, null, 2)}</code>
            </pre>
          </div>
        )}

        {/* 影响分析 */}
        {request.impactSummary && (
          <div className={styles.impact}>
            <WarningOutlined /> {request.impactSummary}
          </div>
        )}

        {/* 消息 */}
        <div className={styles.message}>
          {request.message || `工具「${request.tool}」需要确认`}
        </div>

        {/* 操作按钮 */}
        <div className={styles.actions}>
          <Button
            danger
            icon={<CloseOutlined />}
            onClick={onReject}
            size="small"
          >
            拒绝
          </Button>
          <Button
            type="primary"
            icon={<CheckOutlined />}
            onClick={onApprove}
            size="small"
          >
            允许本次
          </Button>
          <Tooltip title="将此工具+路径+命令加入白名单，下次自动放行">
            <Button
              icon={<SafetyOutlined />}
              onClick={() => {
                const path = extractPath()
                const cmd = extractCommand()
                onWhitelist(path, cmd)
                antMessage.success('已加入白名单')
              }}
              size="small"
            >
              始终允许
            </Button>
          </Tooltip>
        </div>

        {/* 快捷键提示 */}
        <div className={styles.shortcuts}>
          <span>Enter 允许</span>
          <span>Esc 拒绝</span>
        </div>
      </div>
    </div>
  )
}
