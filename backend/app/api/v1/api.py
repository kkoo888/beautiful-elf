"""API v1 路由聚合 - 统一注册所有 endpoint"""
from fastapi import APIRouter

from app.api.v1 import (
    health,
    conversation,
    message,
    pet,
    schedule,
    clipboard,
    snippet,
    notification,
    performance,
    command,
    soul_config,
    skill,
    tool,
    action_log,
    command_usage,
    backup,
    prompt,
    ai_feedback,
    config,
    knowledge,
    memory,
    workflow,
)

api_router = APIRouter()

# 健康检查（路由已包含完整路径，不加 prefix）
api_router.include_router(health.router, tags=["health"])

# 核心业务
api_router.include_router(conversation.router, prefix="/conversations", tags=["conversation"])
api_router.include_router(message.router, prefix="/conversations/{conversation_id}/messages", tags=["message"])
api_router.include_router(schedule.router, prefix="/schedules", tags=["schedule"])
api_router.include_router(clipboard.router, prefix="/clipboard_items", tags=["clipboard"])
api_router.include_router(snippet.router, prefix="/snippets", tags=["snippet"])

# 知识 & 记忆
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["knowledge"])
api_router.include_router(memory.router, prefix="/memory", tags=["memory"])

# AI 相关
api_router.include_router(pet.router, prefix="/pets", tags=["pet"])
api_router.include_router(prompt.router, prefix="/prompts", tags=["prompt"])
api_router.include_router(ai_feedback.router, prefix="/ai_feedback", tags=["ai_feedback"])

# 技能 & 工具 & 工作流
api_router.include_router(skill.router, prefix="/skills", tags=["skill"])
api_router.include_router(tool.router, prefix="/tools", tags=["tool"])
api_router.include_router(workflow.router, prefix="/workflows", tags=["workflow"])

# 系统
api_router.include_router(notification.router, prefix="/notifications", tags=["notification"])
api_router.include_router(performance.router, prefix="/performance", tags=["performance"])
api_router.include_router(command.router, prefix="/commands", tags=["command"])
api_router.include_router(soul_config.router, prefix="/soul_configs", tags=["soul_config"])
api_router.include_router(action_log.router, prefix="/action_logs", tags=["action_log"])
api_router.include_router(command_usage.router, prefix="/command_usage", tags=["command_usage"])
api_router.include_router(backup.router, prefix="/backups", tags=["backup"])

# config 含 /{key} 通配符，放最后
api_router.include_router(config.router, prefix="/configs", tags=["config"])
