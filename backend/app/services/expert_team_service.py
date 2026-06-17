"""专家团工作流 Service — PM 委派模式

架构:
  1. PM（组长）分析任务，输出分配计划
  2. 逐个执行被指派的专家
  3. PM 评估打分
  4. PM 汇总最终报告

WebSocket 实时推送:
  - expert_status: 专家状态变更（开始/完成/失败）
  - expert_thinking: 专家推理过程
  - expert_progress: 任务进度更新
"""
import json
import logging
import re
import uuid
from typing import List, Optional, Tuple, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.repository.expert_team_repo import ExpertTeamRepository
from app.schemas.expert_team import (
    ExpertTeamCreate, ExpertTeamUpdate, ExpertTeamOut, ExpertTeamBindExperts,
    ExpertCreate, ExpertUpdate, ExpertOut,
    ExpertTeamRunOut, ExpertTeamExecuteRequest,
    DiscussionMessage,
    ExpertSkillCreate, ExpertSkillUpdate, ExpertSkillOut, ExpertRoleRunOut,
    PolishPromptRequest,
)
from app.core.exceptions import RecordNotFoundError

logger = logging.getLogger(__name__)


# ─── WebSocket 实时推送辅助 ──────────────────────────────

async def _ws_broadcast(team_id: int, event_type: str, payload: dict):
    """广播专家团执行事件到 WebSocket"""
    try:
        from app.core.websocket_manager import ws_manager
        await ws_manager.broadcast_all({
            "type": event_type,
            "payload": {**payload, "teamId": team_id},
            "timestamp": int(datetime.now().timestamp() * 1000),
            "eventId": str(uuid.uuid4()),
        })
    except Exception as e:
        logger.debug(f"WebSocket 推送失败（非致命）: {e}")


# ─── LLM 调用辅助函数 ──────────────────────────────────

async def _call_llm(db, provider_id: int, model_name: str, prompt: str, temperature: float = 0.7) -> tuple:
    """通过 LLMService 调用 LLM，返回 (content, tokens)"""
    from langchain_core.messages import HumanMessage
    from app.agent.llm_service import llm_service

    llm = await llm_service.get_chat_llm(
        db, provider_id=provider_id, model_name=model_name, temperature=temperature,
    )
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    content = response.content if isinstance(response.content, str) else str(response.content)
    tokens = 0
    if hasattr(response, "usage_metadata") and response.usage_metadata:
        tokens = response.usage_metadata.get("total_tokens", 0)
    return content, tokens


# ─── 模型温度查询 ───────────────────────────────────────

async def _get_model_temperature(db, provider_id: int | None, model_name: str | None) -> float:
    """从 llm_model 表读取模型默认温度，读不到返回 0.7"""
    if not provider_id or not model_name:
        return 0.7
    try:
        from app.repository.llm_model_repo import LLMModelRepository
        repo = LLMModelRepository()
        model = await repo.find_by_provider_and_name(db, provider_id, model_name)
        if model and model.temperature is not None:
            return float(model.temperature)
    except Exception:
        pass
    return 0.7


# ─── Service 主类 ────────────────────────────────────────

class ExpertTeamService:
    """专家团工作流 Service"""

    def __init__(self):
        self.repo = ExpertTeamRepository()

    # ─── 专家团 CRUD ───────────────────────────────────

    async def create_team(self, db: AsyncSession, data: ExpertTeamCreate) -> ExpertTeamOut:
        """创建专家团（可绑定已有专家）"""
        team_data = data.model_dump(exclude={"expert_ids"})
        team = await self.repo.create_team(db, team_data)

        # 绑定专家
        experts = []
        if data.expert_ids:
            await self.repo.replace_team_experts(db, team.id, data.expert_ids)
            experts = await self.repo.find_experts_by_ids(db, data.expert_ids)

        leader = await self.repo.find_expert_by_id(db, team.leader_id) if team.leader_id else None
        return self._to_out_team(team, experts, leader)

    async def get_team_by_id(self, db: AsyncSession, team_id: int) -> ExpertTeamOut:
        team = await self.repo.find_team_by_id(db, team_id)
        if not team:
            raise RecordNotFoundError("专家团不存在")
        experts = await self.repo.find_experts_by_team(db, team_id)
        leader = await self.repo.find_expert_by_id(db, team.leader_id) if team.leader_id else None
        return self._to_out_team(team, experts, leader)

    async def list_teams(
        self, db: AsyncSession, page: int = 1, page_size: int = 20,
        category: Optional[str] = None, enabled: Optional[int] = None,
    ) -> Tuple[List[ExpertTeamOut], int]:
        offset = (page - 1) * page_size
        teams = await self.repo.find_all_teams(db, offset=offset, limit=page_size, category=category, enabled=enabled)
        total = await self.repo.count_teams(db, category=category, enabled=enabled)

        result = []
        for t in teams:
            experts = await self.repo.find_experts_by_team(db, t.id)
            leader = await self.repo.find_expert_by_id(db, t.leader_id) if t.leader_id else None
            result.append(self._to_out_team(t, experts, leader))
        return result, total

    async def update_team(self, db: AsyncSession, team_id: int, data: ExpertTeamUpdate) -> ExpertTeamOut:
        team = await self.repo.find_team_by_id(db, team_id)
        if not team:
            raise RecordNotFoundError("专家团不存在")
        update_data = data.model_dump(exclude_unset=True, by_alias=False)
        # expert_ids 单独处理
        expert_ids = update_data.pop("expert_ids", None)
        if update_data:
            team = await self.repo.update_team(db, team_id, update_data)
        # 同步专家绑定：整体替换模式
        if expert_ids is not None:
            await self.repo.replace_team_experts(db, team_id, expert_ids)
        experts = await self.repo.find_experts_by_team(db, team_id)
        leader = await self.repo.find_expert_by_id(db, team.leader_id) if team.leader_id else None
        return self._to_out_team(team, experts, leader)

    async def delete_team(self, db: AsyncSession, team_id: int) -> bool:
        team = await self.repo.find_team_by_id(db, team_id)
        if not team:
            raise RecordNotFoundError("专家团不存在")
        await self.repo.soft_delete_bindings_by_team(db, team_id)
        return await self.repo.soft_delete_team(db, team_id)

    async def bind_experts(self, db: AsyncSession, team_id: int, data: ExpertTeamBindExperts) -> ExpertTeamOut:
        """绑定专家到专家团"""
        team = await self.repo.find_team_by_id(db, team_id)
        if not team:
            raise RecordNotFoundError("专家团不存在")
        await self.repo.replace_team_experts(db, team_id, data.expert_ids)
        experts = await self.repo.find_experts_by_team(db, team_id)
        return self._to_out_team(team, experts)

    # ─── 专家 CRUD（独立实体）─────────────────────────

    async def create_expert(self, db: AsyncSession, data: ExpertCreate) -> ExpertOut:
        """创建专家"""
        expert_data = data.model_dump(by_alias=False)
        # 温度未填时，从 llm_model 读取模型默认温度
        if expert_data.get("provider_id") and expert_data.get("model_name"):
            expert_data["temperature"] = await _get_model_temperature(
                db, expert_data["provider_id"], expert_data["model_name"]
            )
        expert = await self.repo.create_expert(db, expert_data)
        return self._to_out_expert(expert)

    async def get_expert_by_id(self, db: AsyncSession, expert_id: int) -> ExpertOut:
        expert = await self.repo.find_expert_by_id(db, expert_id)
        if not expert:
            raise RecordNotFoundError("专家不存在")
        return self._to_out_expert(expert)

    async def list_experts(
        self, db: AsyncSession, page: int = 1, page_size: int = 20,
        enabled: Optional[int] = None,
    ) -> Tuple[List[ExpertOut], int]:
        offset = (page - 1) * page_size
        experts = await self.repo.find_all_experts(db, offset=offset, limit=page_size, enabled=enabled)
        total = await self.repo.count_experts(db, enabled=enabled)
        return [self._to_out_expert(e) for e in experts], total

    async def update_expert(self, db: AsyncSession, expert_id: int, data: ExpertUpdate) -> ExpertOut:
        expert = await self.repo.find_expert_by_id(db, expert_id)
        if not expert:
            raise RecordNotFoundError("专家不存在")
        update_data = data.model_dump(exclude_unset=True, by_alias=False)
        if update_data:
            expert = await self.repo.update_expert(db, expert_id, update_data)
        return self._to_out_expert(expert)

    async def delete_expert(self, db: AsyncSession, expert_id: int) -> bool:
        expert = await self.repo.find_expert_by_id(db, expert_id)
        if not expert:
            raise RecordNotFoundError("专家不存在")
        return await self.repo.soft_delete_expert(db, expert_id)

    async def polish_prompt(self, db: AsyncSession, data: PolishPromptRequest) -> str:
        """润色提示词 — 调用默认大模型优化"""
        from app.services.llm_provider_service import LLMProviderService
        provider_service = LLMProviderService()
        default_provider = await provider_service.get_default_provider(db)
        if not default_provider:
            raise ValueError("请先在设置中配置默认 AI 供应商")
        provider_id = default_provider.id
        model_name = ""
        if default_provider.models:
            enabled_models = [m for m in default_provider.models if m.is_enabled == 1]
            if enabled_models:
                model_name = enabled_models[0].model_name
        if not model_name:
            raise ValueError("默认供应商没有可用的模型")

        polish_system = (
            "优化用户的提示词，使其更清晰、专业、可执行，保持原意不变。\n"
            "要求：\n"
            "- 直接输出优化后的提示词正文\n"
            "- 禁止输出任何标题、角色说明、格式标记、编号、前缀或后缀\n"
            "- 禁止使用 #、##、**、``` 等 markdown 格式\n"
            "- 只返回纯文本内容\n\n"
            "【图生图场景 — 如果提示词涉及修改/转换现有图片，请使用以下结构】\n"
            "推荐结构：[修改要求] + [新风格/新场景] + [需要添加或移除的元素] + [需要保留的元素]\n"
            "示例：将白天街景转换为电影级赛博朋克夜景，添加霓虹灯和湿漉漉的路面倒影，同时保留原始街道布局、拍摄角度和主要建筑形状。\n\n"
            "【高信息密度图片 — 复杂画面建议包含以下要素】\n"
            "主体 | 背景环境 | 重要次要元素 | 风格和光照 | 构图约束 | 需要保留的元素"
        )
        prompt = f"{polish_system}\n\n原始提示词：\n{data.content}"
        content, _ = await _call_llm(db, provider_id, model_name, prompt, temperature=0.3)
        return content.strip()

    # ─── 专家技能绑定 ─────────────────────────────────

    async def list_expert_skills(self, db: AsyncSession, expert_id: int) -> list:
        """查询专家绑定的技能（含技能详情）"""
        binds = await self.repo.find_skills_by_expert(db, expert_id)
        result = []
        for b in binds:
            skill = await self._get_skill_info(db, b.skill_id)
            result.append({
                "id": b.id,
                "expertId": b.expert_id,
                "skillId": b.skill_id,
                "skillName": skill.get("name", "") if skill else "",
                "skillDisplayName": skill.get("display_name", "") if skill else "",
                "skillDescription": skill.get("description", "") if skill else "",
                "priority": b.priority,
                "configOverride": b.config_override,
                "isEnabled": b.is_enabled,
                "createdAt": str(b.created_at) if b.created_at else None,
                "updatedAt": str(b.updated_at) if b.updated_at else None,
            })
        return result

    async def bind_skill(self, db: AsyncSession, expert_id: int, data: ExpertSkillCreate) -> ExpertSkillOut:
        """绑定技能到专家"""
        expert = await self.repo.find_expert_by_id(db, expert_id)
        if not expert:
            raise RecordNotFoundError("专家不存在")
        bind_data = data.model_dump(by_alias=False)
        bind_data["expert_id"] = expert_id
        # 检查是否已绑定
        existing = await self.repo.find_skill_bind(db, expert_id, data.skill_id)
        if existing:
            # 更新已有绑定
            bind = await self.repo.update_skill_bind(db, existing.id, bind_data)
        else:
            bind = await self.repo.create_skill_bind(db, bind_data)
        return self._to_out_skill_bind(bind)

    async def update_skill_bind(self, db: AsyncSession, bind_id: int, data: ExpertSkillUpdate) -> ExpertSkillOut:
        """更新专家技能绑定"""
        bind = await self.repo.find_skill_bind_by_id(db, bind_id)
        if not bind:
            raise RecordNotFoundError("技能绑定不存在")
        update_data = data.model_dump(exclude_unset=True, by_alias=False)
        if update_data:
            bind = await self.repo.update_skill_bind(db, bind_id, update_data)
        return self._to_out_skill_bind(bind)

    async def unbind_skill(self, db: AsyncSession, bind_id: int) -> bool:
        """解绑技能"""
        bind = await self.repo.find_skill_bind_by_id(db, bind_id)
        if not bind:
            raise RecordNotFoundError("技能绑定不存在")
        return await self.repo.soft_delete_skill_bind(db, bind_id)

    async def _get_skill_info(self, db: AsyncSession, skill_id: int) -> Optional[dict]:
        """获取技能基本信息"""
        from app.repository.skill_repo import SkillRepository
        skill_repo = SkillRepository()
        skill = await skill_repo.find_by_id(db, skill_id)
        if not skill:
            return None
        return {
            "id": skill.id,
            "name": skill.name,
            "display_name": skill.display_name,
            "description": skill.description,
        }

    # ─── 角色执行记录 ─────────────────────────────────

    async def list_role_runs(self, db: AsyncSession, run_id: int) -> list[ExpertRoleRunOut]:
        """查询某次运行的所有角色执行记录"""
        # 先校验 run 存在
        run = await self.repo.find_run_by_id(db, run_id)
        if not run:
            raise RecordNotFoundError("运行记录不存在")
        runs = await self.repo.find_role_runs_by_run(db, run_id)
        return [self._to_out_role_run(r) for r in runs]

    async def _create_role_run(self, db: AsyncSession, run_id: int, role_id: int, role_name: str, round_num: int) -> object:
        """创建角色执行记录"""
        return await self.repo.create_role_run(db, {
            "run_id": run_id,
            "role_id": role_id,
            "role_name": role_name,
            "run_status": 1,  # 运行中
            "round_num": round_num,
            "started_at": datetime.now(),
        })

    async def _finish_role_run(self, db: AsyncSession, role_run_id: int, status: int,
                                output: str = "", skills_used: list = None,
                                error: str = "", tokens: int = 0) -> None:
        """完成角色执行记录"""
        await self.repo.update_role_run(db, role_run_id, {
            "run_status": status,
            "output_json": {"output": output} if output else None,
            "skills_used": skills_used or [],
            "error_message": error[:2048] if error else "",
            "finished_at": datetime.now(),
            "token_usage": tokens,
        })

    def _to_out_skill_bind(self, bind) -> ExpertSkillOut:
        return ExpertSkillOut.model_validate(bind)

    def _to_out_role_run(self, run) -> ExpertRoleRunOut:
        return ExpertRoleRunOut.model_validate(run)

    # ─── 执行专家团（PM 委派模式）────────────────────

    async def execute_team(
        self, db: AsyncSession, team_id: int, request: ExpertTeamExecuteRequest,
        on_progress: Any = None,
    ) -> dict:
        """执行专家团工作流 — PM 委派模式

        流程:
          1. PM（组长）分析任务，输出分配计划
          2. 逐个执行被指派的专家
          3. PM 评估打分
          4. 不达标则返工（带改进建议），达标则 PM 汇总报告

        Args:
            on_progress: 可选回调 async def on_progress(event: dict)
                         实时推送 SSE 事件（expert_start / expert_done / pm_thinking / pm_done）
        """
        team = await self.repo.find_team_by_id(db, team_id)
        if not team:
            raise RecordNotFoundError("专家团不存在")

        # 加载组长（PM）
        leader = None
        if team.leader_id:
            leader = await self.repo.find_expert_by_id(db, team.leader_id)
        if not leader:
            raise RecordNotFoundError("专家团未设置组长，请先绑定组长")

        # 加载团队专家（不含组长本身）
        experts = await self.repo.find_experts_by_team(db, team_id)
        enabled_experts = [e for e in experts if e.is_enabled == 1 and e.id != leader.id]
        if not enabled_experts:
            raise RecordNotFoundError("专家团没有可用的专家成员")

        max_rounds = request.max_rounds or team.max_rounds

        # 解析默认供应商模型（专家未配模型时回退用）
        from app.services.llm_provider_service import LLMProviderService
        provider_service = LLMProviderService()
        default_provider = await provider_service.get_default_provider(db)
        default_provider_id = default_provider.id if default_provider else 0
        default_model_name = ""
        if default_provider and default_provider.models:
            enabled_models = [m for m in default_provider.models if m.is_enabled == 1]
            if enabled_models:
                default_model_name = enabled_models[0].model_name

        # PM 的模型配置（组长专家的配置，回退到默认）
        pm_provider_id = leader.provider_id or default_provider_id
        pm_model_name = leader.model_name or default_model_name
        pm_temperature = leader.temperature or 0.3

        # 创建运行记录
        run = await self.repo.create_run(db, {
            "team_id": team_id,
            "run_status": 1,
            "trigger_type": 0,
            "input_text": request.input_text,
        })

        start_time = datetime.now()
        total_tokens = 0
        discussion: list[dict] = []

        try:
            # 序列化专家信息
            experts_data = [self._to_out_expert(e).model_dump() for e in enabled_experts]

            # 批量加载技能绑定
            expert_ids = [e["id"] for e in experts_data]
            all_skills = await self.repo.find_skills_by_experts(db, expert_ids)
            skills_by_expert: dict[int, list] = {}
            for s in all_skills:
                skills_by_expert.setdefault(s.expert_id, []).append(s)
            for e in experts_data:
                binds = skills_by_expert.get(e["id"], [])
                e["skills"] = []
                for b in binds:
                    skill_info = await self._get_skill_info(db, b.skill_id)
                    if skill_info:
                        skill_info["priority"] = b.priority
                        skill_info["config_override"] = b.config_override
                        e["skills"].append(skill_info)

            expert_list_str = ", ".join([
                f"ID={e['id']} {e['member_name']}({e['member_role']})" for e in experts_data
            ])

            # ── 确保工具注册表已加载 ──
            from app.agent.tool_registry import tool_registry
            if not tool_registry._db_loaded:
                await tool_registry.load_from_db(db)

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # Step 1: PM 分析任务，输出分配计划
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            await _ws_broadcast(team_id, "expert_status", {
                "expertName": leader.member_name,
                "expertRole": "PM/组长",
                "status": "running",
                "round": 0,
                "runId": run.id,
            })

            pm_system = leader.system_prompt or "你是一位资深项目经理（PM），擅长任务拆解和资源调度。"
            orchestrator_prompt = team.orchestrator_prompt or ""

            # 如果团队没配 orchestrator_prompt，用默认模板
            if not orchestrator_prompt:
                orchestrator_prompt = (
                    "请分析用户任务，决定分配给团队中的哪些专家，以及每个专家需要完成的子任务。\n"
                    "输出 JSON 格式：\n"
                    '{{"assignments": [{{"expert_id": ID, "subtask": "具体子任务描述", "priority": 1}}], "analysis": "任务分析"}}'
                )

            analyze_prompt = f"""{pm_system}

## 团队成员
{expert_list_str}

## 工作指令
{orchestrator_prompt}

## 用户任务
{request.input_text}

请分析任务并输出分配计划（JSON 格式）。"""

            plan_content, plan_tokens = await _call_llm(
                db, pm_provider_id, pm_model_name, analyze_prompt, temperature=pm_temperature,
            )
            total_tokens += plan_tokens

            # 记录 PM 分析
            discussion.append({
                "round": 0,
                "expertName": leader.member_name,
                "expertRole": "PM/组长",
                "content": plan_content,
                "timestamp": datetime.now().isoformat(),
            })

            await _ws_broadcast(team_id, "expert_thinking", {
                "expertName": leader.member_name,
                "expertRole": "PM/组长",
                "round": 0,
                "content": plan_content,
                "runId": run.id,
            })
            await _ws_broadcast(team_id, "expert_status", {
                "expertName": leader.member_name,
                "expertRole": "PM/组长",
                "status": "done",
                "round": 0,
                "runId": run.id,
            })

            # 回调：PM 分析完成
            if on_progress:
                await on_progress({"type": "pm_done", "expertName": leader.member_name, "content": plan_content})

            # 解析分配计划
            assignments = self._parse_assignments(plan_content, experts_data)

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # Step 2: 逐个执行被指派的专家
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            expert_outputs: list[dict] = []  # {expert_id, expert_name, subtask, output, tokens}

            for assign in assignments:
                expert_id = assign["expert_id"]
                subtask = assign["subtask"]
                member = next((e for e in experts_data if e["id"] == expert_id), None)
                if not member:
                    logger.warning(f"分配计划中的专家 ID={expert_id} 不存在，跳过")
                    continue

                # 推送：专家开始
                await _ws_broadcast(team_id, "expert_status", {
                    "expertName": member["member_name"],
                    "expertRole": member["member_role"],
                    "avatar": member.get("avatar", "🤖"),
                    "status": "running",
                    "round": 1,
                    "runId": run.id,
                })

                # 回调：专家开始
                if on_progress:
                    await on_progress({
                        "type": "expert_start",
                        "expertName": member["member_name"],
                        "expertRole": member["member_role"],
                        "avatar": member.get("avatar", "🤖"),
                        "subtask": subtask,
                    })

                # 创建角色执行记录
                role_run = await self._create_role_run(db, run.id, member["id"], member["member_name"], 1)

                # 构建专家 prompt
                expert_system = member.get("system_prompt") or f"你是{member['member_name']}，角色是{member['member_role']}。"
                expert_prompt = f"""{expert_system}

## 你的任务
{subtask}

## 原始用户问题
{request.input_text}

请从你的专业角度，完成以上任务。"""

                # 专家的模型配置
                expert_provider_id = member.get("provider_id") or default_provider_id
                expert_model_name = member.get("model_name") or default_model_name
                expert_temperature = float(member.get("temperature") or 0.7)

                exp_start = datetime.now()
                try:
                    content, tokens = await _call_llm(
                        db, expert_provider_id, expert_model_name, expert_prompt, temperature=expert_temperature,
                    )
                    total_tokens += tokens
                    duration_ms = int((datetime.now() - exp_start).total_seconds() * 1000)

                    await self._finish_role_run(db, role_run.id, status=2, output=content, tokens=tokens)

                    expert_outputs.append({
                        "expert_id": expert_id,
                        "expert_name": member["member_name"],
                        "expert_role": member["member_role"],
                        "subtask": subtask,
                        "output": content,
                        "tokens": tokens,
                    })
                    discussion.append({
                        "round": 1,
                        "expertName": member["member_name"],
                        "expertRole": member["member_role"],
                        "content": content,
                        "timestamp": datetime.now().isoformat(),
                    })

                except Exception as e:
                    logger.error(f"专家 {member['member_name']} 执行失败: {e}")
                    content = f"[执行失败: {e}]"
                    tokens = 0
                    duration_ms = int((datetime.now() - exp_start).total_seconds() * 1000)
                    await self._finish_role_run(db, role_run.id, status=3, error=str(e))
                    expert_outputs.append({
                        "expert_id": expert_id,
                        "expert_name": member["member_name"],
                        "expert_role": member["member_role"],
                        "subtask": subtask,
                        "output": content,
                        "tokens": 0,
                    })

                # 推送：专家完成
                await _ws_broadcast(team_id, "expert_thinking", {
                    "expertName": member["member_name"],
                    "expertRole": member["member_role"],
                    "avatar": member.get("avatar", "🤖"),
                    "round": 1,
                    "content": content,
                    "runId": run.id,
                    "durationMs": duration_ms,
                })
                await _ws_broadcast(team_id, "expert_status", {
                    "expertName": member["member_name"],
                    "expertRole": member["member_role"],
                    "avatar": member.get("avatar", "🤖"),
                    "status": "done",
                    "round": 1,
                    "runId": run.id,
                    "durationMs": duration_ms,
                })

                # 回调：专家完成
                if on_progress:
                    await on_progress({
                        "type": "expert_done",
                        "expertName": member["member_name"],
                        "expertRole": member["member_role"],
                        "avatar": member.get("avatar", "🤖"),
                        "content": content,
                        "durationMs": duration_ms,
                    })

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # Step 3: PM 评估打分
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            await _ws_broadcast(team_id, "expert_status", {
                "expertName": leader.member_name,
                "expertRole": "PM/组长",
                "status": "running",
                "round": -1,
                "runId": run.id,
            })

            expert_results_text = "\n\n".join([
                f"### {o['expert_name']}({o['expert_role']}) — 子任务: {o['subtask']}\n{o['output']}"
                for o in expert_outputs
            ])

            eval_prompt = f"""{pm_system}

## 用户原始任务
{request.input_text}

## 专家完成情况
{expert_results_text}

请评估每个专家的完成质量，打分（1-10），并判断是否达标。
输出 JSON 格式：
{{"scores": [{{"expert_id": ID, "score": 分数, "feedback": "评价"}}], "overall_pass": true/false, "reason": "总体评价"}}"""

            eval_content, eval_tokens = await _call_llm(
                db, pm_provider_id, pm_model_name, eval_prompt, temperature=pm_temperature,
            )
            total_tokens += eval_tokens

            discussion.append({
                "round": -1,
                "expertName": leader.member_name,
                "expertRole": "PM/组长(评估)",
                "content": eval_content,
                "timestamp": datetime.now().isoformat(),
            })

            await _ws_broadcast(team_id, "expert_thinking", {
                "expertName": leader.member_name,
                "expertRole": "PM/组长",
                "round": -1,
                "content": eval_content,
                "runId": run.id,
            })

            # 回调：PM 评估完成
            if on_progress:
                await on_progress({"type": "pm_eval", "expertName": leader.member_name, "content": eval_content})

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # Step 4: PM 汇总最终报告
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            synthesizer_prompt = team.synthesizer_prompt or ""
            if not synthesizer_prompt:
                synthesizer_prompt = "请综合所有专家的分析结果，生成结构化的最终报告，包含：核心结论、各专家观点摘要、关键建议。"

            report_prompt = f"""{pm_system}

## 用户原始任务
{request.input_text}

## 专家分析结果
{expert_results_text}

## 评估结果
{eval_content}

## 工作指令
{synthesizer_prompt}

请生成最终报告。"""

            report_content, report_tokens = await _call_llm(
                db, pm_provider_id, pm_model_name, report_prompt, temperature=pm_temperature,
            )
            total_tokens += report_tokens

            await _ws_broadcast(team_id, "expert_status", {
                "expertName": leader.member_name,
                "expertRole": "PM/组长",
                "status": "done",
                "round": -1,
                "runId": run.id,
            })
            await _ws_broadcast(team_id, "expert_progress", {
                "status": "completed",
                "runId": run.id,
                "output": report_content[:500],
            })

            # 回调：PM 报告完成
            if on_progress:
                await on_progress({"type": "pm_report", "content": report_content})

            # ── 汇总结果 ──
            end_time = datetime.now()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)

            result = {
                "runId": run.id,
                "status": 2,
                "output": report_content,
                "discussion": discussion,
                "rounds": 1,
                "tokenUsage": total_tokens,
                "durationMs": duration_ms,
            }

            await self.repo.update_run(db, run.id, {
                "run_status": 2,
                "output_text": report_content,
                "discussion_json": discussion,
                "round_count": 1,
                "token_usage": total_tokens,
                "started_at": run.created_at,
                "finished_at": end_time,
                "duration_ms": duration_ms,
            })

            return result

        except Exception as e:
            logger.error(f"专家团执行失败: {e}", exc_info=True)
            await self.repo.update_run(db, run.id, {
                "run_status": 3,
                "error_message": str(e)[:2048],
                "finished_at": datetime.now(),
            })
            raise

    @staticmethod
    def _parse_assignments(pm_output: str, experts_data: list[dict]) -> list[dict]:
        """解析 PM 输出的分配计划 JSON

        PM 输出格式:
        {"assignments": [{"expert_id": 1, "subtask": "...", "priority": 1}], "analysis": "..."}
        """
        import json as _json
        import re

        # 尝试从 PM 输出中提取 JSON
        try:
            # 先尝试直接解析
            data = _json.loads(pm_output)
        except _json.JSONDecodeError:
            # 尝试从 markdown code block 中提取
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', pm_output, re.DOTALL)
            if json_match:
                data = _json.loads(json_match.group(1))
            else:
                # 尝试找任何 JSON 对象
                json_match = re.search(r'\{[^{}]*"assignments"[^{}]*\[.*?\][^{}]*\}', pm_output, re.DOTALL)
                if json_match:
                    data = _json.loads(json_match.group())
                else:
                    # fallback: 给每个专家分配原始任务
                    logger.warning(f"PM 输出无法解析为 JSON，fallback 为全员分配")
                    return [
                        {"expert_id": e["id"], "subtask": f"分析: {pm_output[:200]}"}
                        for e in experts_data
                    ]

        assignments = data.get("assignments", [])
        if not assignments:
            # fallback
            return [
                {"expert_id": e["id"], "subtask": f"分析: {pm_output[:200]}"}
                for e in experts_data
            ]

        return assignments

    # ─── 运行记录查询 ──────────────────────────────────

    async def get_run_by_id(self, db: AsyncSession, run_id: int) -> ExpertTeamRunOut:
        run = await self.repo.find_run_by_id(db, run_id)
        if not run:
            raise RecordNotFoundError("运行记录不存在")
        return self._to_out_run(run)

    async def list_runs_by_team(
        self, db: AsyncSession, team_id: int, page: int = 1, page_size: int = 20,
    ) -> Tuple[List[ExpertTeamRunOut], int]:
        offset = (page - 1) * page_size
        runs = await self.repo.find_runs_by_team(db, team_id, offset=offset, limit=page_size)
        total = await self.repo.count_runs_by_team(db, team_id)
        return [self._to_out_run(r) for r in runs], total

    async def list_all_runs(
        self, db: AsyncSession, page: int = 1, page_size: int = 20, status: Optional[int] = None,
    ) -> Tuple[List[ExpertTeamRunOut], int]:
        offset = (page - 1) * page_size
        runs = await self.repo.find_all_runs(db, offset=offset, limit=page_size, status=status)
        total = await self.repo.count_all_runs(db, status=status)
        return [self._to_out_run(r) for r in runs], total

    # ─── Pydantic 序列化（替代手动 dict）──────────────

    @staticmethod
    def _to_out_team(team, experts=None, leader=None) -> ExpertTeamOut:
        """序列化专家团（含组长）"""
        team_out = ExpertTeamOut.model_validate(team)
        team_out.experts = [ExpertTeamService._to_out_expert(e) for e in (experts or [])]
        if leader:
            team_out.leader = ExpertTeamService._to_out_expert(leader)
        return team_out

    @staticmethod
    def _to_out_expert(expert) -> ExpertOut:
        """用 Pydantic schema 序列化专家"""
        return ExpertOut.model_validate(expert)

    @staticmethod
    def _to_out_run(run) -> ExpertTeamRunOut:
        """用 Pydantic schema 序列化运行记录"""
        return ExpertTeamRunOut.model_validate(run)
