/**
 * API 错误处理工具
 * 统一错误码匹配中文提示（符合阿里巴巴 API 规范）
 */

/** 错误码 → 中文提示映射（新规范：MODULE_ERROR_TYPE） */
const ERROR_MESSAGES: Record<string, string> = {
  // 系统级
  SYSTEM_INTERNAL_ERROR: '系统繁忙，请稍后重试',
  SYSTEM_STORAGE_ERROR: '存储服务异常，请稍后重试',
  SYSTEM_NOT_FOUND: '请求的资源不存在',
  SYSTEM_DUPLICATE: '该记录已存在，请勿重复创建',
  SYSTEM_CONSISTENCY: '数据异常，请稍后重试',
  SYSTEM_VALIDATION: '请检查输入参数是否正确',

  // 认证
  AUTH_REQUIRED: '请先登录',
  AUTH_EXPIRED: '登录已过期，请重新登录',
  AUTH_INVALID: '用户名或密码错误',
  AUTH_FORBIDDEN: '没有权限执行此操作',

  // 业务模块
  PET_ERROR: '宠物系统异常，请稍后重试',
  SCHEDULE_ERROR: '日程系统异常，请稍后重试',
  SKILL_ERROR: '技能执行失败，请检查配置',
  WORKFLOW_ERROR: '工作流执行失败，请检查配置',
  INTENT_NOT_FOUND: '意图不存在',

  // AI
  AI_TIMEOUT: 'AI 服务繁忙，请稍后重试',
  AI_RAG_INDEX_ERROR: '知识库索引异常，请联系管理员',

  // 兼容旧错误码
  UNKNOWN_ERROR: '未知错误，请稍后重试',
  NETWORK_ERROR: '网络连接失败，请检查网络',
  TIMEOUT_ERROR: '请求超时，请稍后重试',
  NOT_FOUND: '请求的资源不存在',
  ALREADY_EXISTS: '资源已存在',
  VALIDATION_ERROR: '参数校验失败',
}

export class ApiError extends Error {
  code: string
  userTip: string
  statusCode?: number

  constructor(code: string, message?: string, statusCode?: number, userTip?: string) {
    super(message || ERROR_MESSAGES[code] || ERROR_MESSAGES.UNKNOWN_ERROR)
    this.name = 'ApiError'
    this.code = code
    this.statusCode = statusCode
    this.userTip = userTip || ERROR_MESSAGES[code] || '请稍后重试'
  }
}

/**
 * 从 API 响应中提取错误信息
 * 优先使用后端返回的 user_tip（用户友好提示）
 */
export function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.userTip || error.message
  }

  if (error instanceof Error) {
    const axiosError = error as {
      response?: {
        data?: {
          code?: string
          message?: string
          user_tip?: string
        }
      }
    }
    if (axiosError.response?.data) {
      const { code, message, user_tip } = axiosError.response.data
      // 优先用 user_tip（给用户看的）
      if (user_tip) return user_tip
      // 其次用错误码映射
      if (code && ERROR_MESSAGES[code]) return ERROR_MESSAGES[code]
      // 最后用 message
      if (message) return message
    }
    return error.message
  }

  return ERROR_MESSAGES.UNKNOWN_ERROR
}

/**
 * 处理 API 错误并返回中文提示
 */
export function handleApiError(error: unknown): string {
  const message = getErrorMessage(error)
  console.error('[API Error]', message, error)
  return message
}
