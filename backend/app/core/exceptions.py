"""统一异常处理"""


class AppError(Exception):
    """应用异常基类"""
    code: str = "APP_ERROR"
    message: str = "应用错误"
    status_code: int = 500

    def __init__(self, message: str = None, **kwargs):
        self.message = message or self.__class__.message
        super().__init__(self.message)


# ============ Mapper 层异常 ============
class StorageError(AppError):
    """存储层通用异常"""
    code = "SYSTEM_STORAGE_ERROR"
    status_code = 500
    message = "存储服务异常"


# ============ Repository 层异常 ============
class RecordNotFoundError(AppError):
    code = "SYSTEM_NOT_FOUND"
    status_code = 404
    message = "记录不存在"


class DuplicateEntryError(AppError):
    code = "SYSTEM_DUPLICATE"
    status_code = 409
    message = "记录已存在"


class DataConsistencyError(AppError):
    code = "SYSTEM_CONSISTENCY"
    status_code = 500
    message = "数据一致性错误"


# ============ 业务异常 ============
class IntentNotFoundError(AppError):
    code = "INTENT_NOT_FOUND"
    status_code = 404
    message = "意图不存在"


class OllamaTimeoutError(AppError):
    code = "OLLAMA_TIMEOUT"
    status_code = 503
    message = "AI 模型响应超时"


class RagIndexError(AppError):
    code = "RAG_INDEX_ERROR"
    status_code = 500
    message = "RAG 索引错误"


class WorkflowError(AppError):
    code = "WORKFLOW_ERROR"
    status_code = 500
    message = "工作流执行错误"


class SkillError(AppError):
    code = "SKILL_ERROR"
    status_code = 500
    message = "技能执行错误"


class PetError(AppError):
    code = "PET_ERROR"
    status_code = 500
    message = "宠物系统错误"


class ScheduleError(AppError):
    code = "SCHEDULE_ERROR"
    status_code = 500
    message = "日程系统错误"
