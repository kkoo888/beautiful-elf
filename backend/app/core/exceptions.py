"""统一异常处理 — 符合阿里巴巴 API 规范

错误码格式: {MODULE}_{ERROR_TYPE}
"""


class AppError(Exception):
    """应用异常基类"""
    code: str = "SYSTEM_INTERNAL_ERROR"
    message: str = "服务器内部错误"
    user_tip: str = "请稍后重试"
    status_code: int = 500

    def __init__(self, message: str = None, user_tip: str = None, **kwargs):
        self.message = message or self.__class__.message
        self.user_tip = user_tip or self.__class__.user_tip
        super().__init__(self.message)


# ============ 系统级异常 ============

class StorageError(AppError):
    """存储层异常"""
    code = "SYSTEM_STORAGE_ERROR"
    status_code = 500
    message = "存储服务异常"
    user_tip = "系统繁忙，请稍后重试"


class RecordNotFoundError(AppError):
    """记录不存在"""
    code = "SYSTEM_NOT_FOUND"
    status_code = 404
    message = "记录不存在"
    user_tip = "请检查请求的资源是否存在"


class DuplicateEntryError(AppError):
    """重复记录"""
    code = "SYSTEM_DUPLICATE"
    status_code = 409
    message = "记录已存在"
    user_tip = "该记录已存在，请勿重复创建"


class DataConsistencyError(AppError):
    """数据一致性错误"""
    code = "SYSTEM_CONSISTENCY"
    status_code = 500
    message = "数据一致性错误"
    user_tip = "系统繁忙，请稍后重试"


class ValidationError(AppError):
    """参数校验失败"""
    code = "SYSTEM_VALIDATION"
    status_code = 400
    message = "参数校验失败"
    user_tip = "请检查输入参数是否正确"


# ============ 业务异常 ============

class IntentNotFoundError(AppError):
    code = "INTENT_NOT_FOUND"
    status_code = 404
    message = "意图不存在"
    user_tip = "请检查意图 ID"


class OllamaTimeoutError(AppError):
    code = "AI_TIMEOUT"
    status_code = 503
    message = "AI 模型响应超时"
    user_tip = "AI 服务繁忙，请稍后重试"


class RagIndexError(AppError):
    code = "AI_RAG_INDEX_ERROR"
    status_code = 500
    message = "RAG 索引错误"
    user_tip = "知识库索引异常，请联系管理员"


class WorkflowError(AppError):
    code = "WORKFLOW_ERROR"
    status_code = 500
    message = "工作流执行错误"
    user_tip = "工作流执行失败，请检查配置"


class SkillError(AppError):
    code = "SKILL_ERROR"
    status_code = 500
    message = "技能执行错误"
    user_tip = "技能执行失败，请检查配置"


class PetError(AppError):
    code = "PET_ERROR"
    status_code = 500
    message = "宠物系统错误"
    user_tip = "宠物系统异常，请稍后重试"


class ScheduleError(AppError):
    code = "SCHEDULE_ERROR"
    status_code = 500
    message = "日程系统错误"
    user_tip = "日程系统异常，请稍后重试"


class ExpertTeamError(AppError):
    """专家团系统异常"""
    code = "EXPERT_TEAM_ERROR"
    status_code = 500
    message = "专家团系统错误"
    user_tip = "专家团操作失败，请稍后重试"
