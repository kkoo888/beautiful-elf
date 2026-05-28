/**
 * API 错误处理工具
 * 统一错误码匹配中文提示
 */

/** 错误码 → 中文提示映射 */
const ERROR_MESSAGES: Record<string, string> = {
  // 通用错误
  UNKNOWN_ERROR: '未知错误，请稍后重试',
  NETWORK_ERROR: '网络连接失败，请检查网络',
  TIMEOUT_ERROR: '请求超时，请稍后重试',
  PARSE_ERROR: '数据解析失败',

  // 认证错误
  AUTH_REQUIRED: '请先登录',
  AUTH_EXPIRED: '登录已过期，请重新登录',
  AUTH_INVALID: '用户名或密码错误',
  AUTH_FORBIDDEN: '没有权限执行此操作',

  // 业务错误
  NOT_FOUND: '请求的资源不存在',
  ALREADY_EXISTS: '资源已存在',
  VALIDATION_ERROR: '参数校验失败',
  RATE_LIMITED: '请求过于频繁，请稍后重试',

  // 知识库错误
  FILE_TOO_LARGE: '文件大小超出限制',
  FILE_TYPE_UNSUPPORTED: '不支持的文件类型',
  UPLOAD_FAILED: '文件上传失败',

  // 工作流错误
  WORKFLOW_INVALID: '工作流配置无效',
  WORKFLOW_RUNNING: '工作流正在运行中',
  WORKFLOW_TIMEOUT: '工作流执行超时',

  // 子代理错误
  AGENT_BUSY: '子代理正忙，请稍后重试',
  AGENT_FAILED: '子代理执行失败',

  // Ollama 错误
  OLLAMA_UNAVAILABLE: 'Ollama 服务不可用',
  OLLAMA_MODEL_NOT_FOUND: '模型未找到，请检查配置',
  OLLAMA_GENERATE_FAILED: '模型生成失败',
}

export class ApiError extends Error {
  code: string
  statusCode?: number

  constructor(code: string, message?: string, statusCode?: number) {
    super(message || ERROR_MESSAGES[code] || ERROR_MESSAGES.UNKNOWN_ERROR)
    this.name = 'ApiError'
    this.code = code
    this.statusCode = statusCode
  }
}

/**
 * 从 API 响应中提取错误信息
 */
export function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message
  }

  if (error instanceof Error) {
    // Axios 错误
    const axiosError = error as { response?: { data?: { code?: string; message?: string } } }
    if (axiosError.response?.data) {
      const { code, message } = axiosError.response.data
      if (code && ERROR_MESSAGES[code]) {
        return ERROR_MESSAGES[code]
      }
      if (message) {
        return message
      }
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
