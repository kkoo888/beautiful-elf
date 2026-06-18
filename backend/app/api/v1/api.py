"""API v1 路由聚合 - 统一注册所有 endpoint"""
from fastapi import APIRouter

from app.api.v1 import (
    health,
    conversation,
    message,
    chat,
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
    markdown_memory,
    memory_entity,
    workflow,
    expert_team,
    ollama,
    llm_provider,
    intent,
    auth,
    debug,
    image_gallery,
    video_gallery,
)

api_router = APIRouter()

# 健康检查（路由已包含完整路径，不加 prefix）
api_router.include_router(health.router, tags=["health"])

# 认证（公开接口，不需要 token）
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])

# 核心业务
api_router.include_router(conversation.router, prefix="/conversations", tags=["conversation"])
api_router.include_router(message.router, prefix="/messages", tags=["message"])
api_router.include_router(chat.router, prefix="", tags=["chat"])
api_router.include_router(schedule.router, prefix="/schedules", tags=["schedule"])
api_router.include_router(clipboard.router, prefix="/clipboard_items", tags=["clipboard"])
api_router.include_router(snippet.router, prefix="/snippets", tags=["snippet"])

# 知识 & 记忆
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["knowledge"])
api_router.include_router(memory.router, prefix="/memories", tags=["memory"])
api_router.include_router(markdown_memory.router, prefix="/markdown_memories", tags=["markdown_memory"])
api_router.include_router(memory_entity.router, prefix="/memory", tags=["memory_entity"])

# AI 相关
api_router.include_router(pet.router, prefix="/pets", tags=["pet"])
api_router.include_router(prompt.router, prefix="/prompts", tags=["prompt"])
api_router.include_router(ai_feedback.router, prefix="/ai_feedback", tags=["ai_feedback"])

# 技能 & 工具 & 工作流
api_router.include_router(skill.router, prefix="/skills", tags=["skill"])
api_router.include_router(tool.router, prefix="/tools", tags=["tool"])
api_router.include_router(workflow.router, prefix="/workflows", tags=["workflow"])
api_router.include_router(expert_team.router, prefix="/expert_teams", tags=["expert_team"])
api_router.include_router(image_gallery.router, prefix="/image_gallery", tags=["image_gallery"])
api_router.include_router(video_gallery.router, prefix="/video_gallery", tags=["video_gallery"])
api_router.include_router(ollama.router, prefix="/ollama", tags=["ollama"])
api_router.include_router(llm_provider.router, prefix="/llm_providers", tags=["llm_provider"])
api_router.include_router(intent.router, prefix="/intents", tags=["intent"])

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

# 调试（开发环境可用，生产环境建议关闭）
api_router.include_router(debug.router, prefix="/debug", tags=["debug"])
