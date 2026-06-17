"""
兼容层 - 旧代码 import from app.models.models 仍然可用
新代码应直接 from app.models.xxx import XxxModel
"""
from app.models.conversation import Conversation, Message
from app.models.memory import MemoryEntry
from app.models.knowledge import KnowledgeDocument, KnowledgeChunk
from app.models.intent import Intent, IntentUsage
from app.models.skill import Skill, SkillStats
from app.models.workflow import Workflow, WorkflowRun, WorkflowStepRun
from app.models.tool import Tool, ToolStats
from app.models.schedule import Schedule
from app.models.clipboard import ClipboardItem
from app.models.snippet import Snippet, SnippetTag
from app.models.pet import PetAttribute, PetInteraction
from app.models.command import Command, CommandUsage
from app.models.performance import PerformanceMetric
from app.models.notification import Notification
from app.models.system import Setting, SoulConfig
from app.models.backup import BackupRecord
from app.models.ai_feedback import AIFeedback
from app.models.prompt import Prompt
from app.models.action_log import ActionLog
from app.models.expert_team import (
    ExpertTeam, Expert, TeamExpertBinding, ExpertTeamRun,
    ExpertSkill, ExpertRoleRun,
)
from app.models.llm_provider import LLMProvider
from app.models.llm_model import LLMModel
from app.models.user import User
from app.models.markdown_memory import MarkdownMemory
from app.models.cost_tracking import CostRecord
from app.models.image_gallery import ImageGallery

__all__ = [
    "Conversation", "Message",
    "MemoryEntry",
    "KnowledgeDocument", "KnowledgeChunk",
    "Intent", "IntentUsage",
    "Skill", "SkillStats",
    "Workflow", "WorkflowRun", "WorkflowStepRun",
    "Tool", "ToolStats",
    "Schedule",
    "ClipboardItem",
    "Snippet", "SnippetTag",
    "PetAttribute", "PetInteraction",
    "Command", "CommandUsage",
    "PerformanceMetric",
    "Notification",
    "Setting", "SoulConfig",
    "BackupRecord",
    "AIFeedback",
    "Prompt",
    "ActionLog",
    "ExpertTeam", "Expert", "TeamExpertBinding", "ExpertTeamRun",
    "ExpertSkill", "ExpertRoleRun",
    "LLMProvider",
    "User",
    "MarkdownMemory",
    "CostRecord",
    "ImageGallery",
]
