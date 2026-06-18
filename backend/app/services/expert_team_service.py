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
        # 检查是否已绑定（有效记录）
        existing = await self.repo.find_skill_bind(db, expert_id, data.skill_id)
        if existing:
            bind = await self.repo.update_skill_bind(db, existing.id, bind_data)
            return self._to_out_skill_bind(bind)
        # 检查是否有软删除的旧记录（唯一键冲突防护）
        deleted = await self.repo.find_skill_bind_any(db, expert_id, data.skill_id)
        if deleted:
            bind = await self.repo.restore_skill_bind(db, deleted.id, bind_data)
            return self._to_out_skill_bind(bind)
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
        """执行专家团工作流 — PM 委派模式（v2: 并行 + 多轮 + 返工 + 技能接入）

        流程（借鉴 CrewAI Hierarchical Process）:
          1. PM 分析任务，输出分配计划
          2. 专家并行执行（asyncio.gather）
          3. PM 评估打分
          4. 不达标 → 带 feedback 重跑不达标专家（最多 max_rounds 轮）
          5. 达标 → PM 汇总最终报告

        Args:
            on_progress: 可选回调 async def on_progress(event: dict)
        """
        import asyncio

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

        # 解析默认供应商模型
        from app.services.llm_provider_service import LLMProviderService
        provider_service = LLMProviderService()
        default_provider = await provider_service.get_default_provider(db)
        default_provider_id = default_provider.id if default_provider else 0
        default_model_name = ""
        if default_provider and default_provider.models:
            enabled_models = [m for m in default_provider.models if m.is_enabled == 1]
            if enabled_models:
                default_model_name = enabled_models[0].model_name

        # PM 的模型配置
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

            pm_system = leader.system_prompt or "你是一位资深项目经理（PM），擅长任务拆解和资源调度。"
            orchestrator_prompt = team.orchestrator_prompt or ""
            synthesizer_prompt = team.synthesizer_prompt or ""

            # ─────────────────────────────────────────
            # 内部方法：执行单个专家
            # ─────────────────────────────────────────
            async def _run_one_expert(member: dict, subtask: str, round_num: int,
                                      context_text: str = "", feedback_text: str = "") -> dict:
                """执行单个专家，返回结果 dict"""
                expert_name = member["member_name"]
                expert_role = member["member_role"]

                # 推送：专家开始
                await _ws_broadcast(team_id, "expert_status", {
                    "expertName": expert_name, "expertRole": expert_role,
                    "avatar": member.get("avatar", "🤖"),
                    "status": "running", "round": round_num, "runId": run.id,
                })
                if on_progress:
                    await on_progress({
                        "type": "expert_start", "expertName": expert_name,
                        "expertRole": expert_role, "avatar": member.get("avatar", "🤖"),
                        "subtask": subtask,
                    })

                role_run = await self._create_role_run(db, run.id, member["id"], expert_name, round_num)

                # 构建专家 prompt（注入技能 + 上下文 + 反馈）
                expert_system = member.get("system_prompt") or f"你是{expert_name}，角色是{expert_role}。"
                skill_text = ""
                skills = member.get("skills", [])
                if skills:
                    skill_lines = [f"- {s.get('display_name', s.get('name', ''))}: {s.get('description', '')}" for s in skills]
                    skill_text = f"\n\n## 你可用的技能\n{chr(10).join(skill_lines)}"

                context_section = f"\n\n## 之前讨论\n{context_text}" if context_text else ""
                feedback_section = f"\n\n## PM 改进建议（请务必参考）\n{feedback_text}" if feedback_text else ""

                expert_prompt = f"""{expert_system}{skill_text}

## 你的任务
{subtask}

## 原始用户问题
{request.input_text}{context_section}{feedback_section}

请从你的专业角度，完成以上任务。"""

                expert_provider_id = member.get("provider_id") or default_provider_id
                expert_model_name = member.get("model_name") or default_model_name
                expert_temperature = float(member.get("temperature") or 0.7)

                exp_start = datetime.now()
                try:
                    content, tokens = await _call_llm(
                        db, expert_provider_id, expert_model_name, expert_prompt, temperature=expert_temperature,
                    )
                    duration_ms = int((datetime.now() - exp_start).total_seconds() * 1000)
                    await self._finish_role_run(db, role_run.id, status=2, output=content, tokens=tokens)

                    # 推送：专家完成
                    await _ws_broadcast(team_id, "expert_thinking", {
                        "expertName": expert_name, "expertRole": expert_role,
                        "avatar": member.get("avatar", "🤖"),
                        "round": round_num, "content": content, "runId": run.id, "durationMs": duration_ms,
                    })
                    await _ws_broadcast(team_id, "expert_status", {
                        "expertName": expert_name, "expertRole": expert_role,
                        "avatar": member.get("avatar", "🤖"),
                        "status": "done", "round": round_num, "runId": run.id, "durationMs": duration_ms,
                    })
                    if on_progress:
                        await on_progress({
                            "type": "expert_done", "expertName": expert_name,
                            "expertRole": expert_role, "avatar": member.get("avatar", "🤖"),
                            "content": content, "durationMs": duration_ms,
                        })

                    return {
                        "expert_id": member["id"], "expert_name": expert_name,
                        "expert_role": expert_role, "subtask": subtask,
                        "output": content, "tokens": tokens, "status": "done",
                    }
                except Exception as e:
                    logger.error(f"专家 {expert_name} 执行失败: {e}")
                    duration_ms = int((datetime.now() - exp_start).total_seconds() * 1000)
                    await self._finish_role_run(db, role_run.id, status=3, error=str(e))
                    return {
                        "expert_id": member["id"], "expert_name": expert_name,
                        "expert_role": expert_role, "subtask": subtask,
                        "output": f"[执行失败: {e}]", "tokens": 0, "status": "failed",
                    }

            # ─────────────────────────────────────────
            # 内部方法：并行执行一批专家
            # ─────────────────────────────────────────
            async def _run_experts_parallel(assignments: list[dict], round_num: int,
                                            context_text: str = "", feedback_map: dict | None = None) -> list[dict]:
                """并行执行所有被指派的专家（CrewAI async_execution 模式）"""
                tasks = []
                for assign in assignments:
                    expert_id = assign["expert_id"]
                    subtask = assign["subtask"]
                    member = next((e for e in experts_data if e["id"] == expert_id), None)
                    if not member:
                        logger.warning(f"分配计划中的专家 ID={expert_id} 不存在，跳过")
                        continue
                    feedback = (feedback_map or {}).get(expert_id, "")
                    tasks.append(_run_one_expert(member, subtask, round_num, context_text, feedback))

                if not tasks:
                    return []
                # 并行执行所有专家
                results = await asyncio.gather(*tasks, return_exceptions=True)
                outputs = []
                for r in results:
                    if isinstance(r, Exception):
                        logger.error(f"专家执行异常: {r}")
                        continue
                    outputs.append(r)
                return outputs

            # ─────────────────────────────────────────
            # 内部方法：PM 评估
            # ─────────────────────────────────────────
            async def _pm_evaluate(expert_results: list[dict], round_num: int) -> dict:
                """PM 评估专家结果，返回 {overall_pass, scores, reason}"""
                await _ws_broadcast(team_id, "expert_status", {
                    "expertName": leader.member_name, "expertRole": "PM/组长",
                    "status": "running", "round": round_num, "runId": run.id,
                })

                results_text = "\n\n".join([
                    f"### {o['expert_name']}({o['expert_role']}) — 子任务: {o['subtask']}\n{o['output']}"
                    for o in expert_results
                ])

                eval_prompt = f"""{pm_system}

## 用户原始任务
{request.input_text}

## 专家完成情况（第 {round_num} 轮）
{results_text}

请评估每个专家的完成质量，打分（1-10），并判断是否达标。
输出 JSON 格式：
{{"scores": [{{"expert_id": ID, "score": 分数, "feedback": "评价"}}], "overall_pass": true/false, "reason": "总体评价"}}"""

                eval_content, eval_tokens = await _call_llm(
                    db, pm_provider_id, pm_model_name, eval_prompt, temperature=pm_temperature,
                )

                await _ws_broadcast(team_id, "expert_thinking", {
                    "expertName": leader.member_name, "expertRole": "PM/组长",
                    "round": round_num, "content": eval_content, "runId": run.id,
                })
                await _ws_broadcast(team_id, "expert_status", {
                    "expertName": leader.member_name, "expertRole": "PM/组长",
                    "status": "done", "round": round_num, "runId": run.id,
                })
                if on_progress:
                    await on_progress({"type": "pm_eval", "expertName": leader.member_name, "content": eval_content})

                return self._parse_evaluation(eval_content), eval_tokens

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # Step 1: PM 分析任务，输出分配计划
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            await _ws_broadcast(team_id, "expert_status", {
                "expertName": leader.member_name, "expertRole": "PM/组长",
                "status": "running", "round": 0, "runId": run.id,
            })

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

            discussion.append({
                "round": 0, "expertName": leader.member_name,
                "expertRole": "PM/组长", "content": plan_content,
                "timestamp": datetime.now().isoformat(),
            })
            await _ws_broadcast(team_id, "expert_thinking", {
                "expertName": leader.member_name, "expertRole": "PM/组长",
                "round": 0, "content": plan_content, "runId": run.id,
            })
            await _ws_broadcast(team_id, "expert_status", {
                "expertName": leader.member_name, "expertRole": "PM/组长",
                "status": "done", "round": 0, "runId": run.id,
            })
            if on_progress:
                await on_progress({"type": "pm_done", "expertName": leader.member_name, "content": plan_content})

            assignments = self._parse_assignments(plan_content, experts_data)

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # Step 2-4: 多轮执行 + 评估 + 返工
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            expert_outputs: list[dict] = []
            all_round_results: list[dict] = []  # 所有轮次的结果（用于上下文传递）
            feedback_map: dict[int, str] = {}   # expert_id → PM 反馈
            passed = False

            for round_num in range(1, max_rounds + 1):
                # 构建上下文（之前所有轮次的讨论）
                context_text = ""
                if all_round_results:
                    ctx_parts = []
                    for prev in all_round_results:
                        ctx_parts.append(f"### {prev['expert_name']}({prev['expert_role']}) 第{prev.get('round', '?')}轮\n{prev['output']}")
                    context_text = "\n\n".join(ctx_parts)

                # 并行执行专家
                round_results = await _run_experts_parallel(assignments, round_num, context_text, feedback_map)
                total_tokens += sum(r.get("tokens", 0) for r in round_results)

                # 记录讨论
                for r in round_results:
                    r["round"] = round_num
                    all_round_results.append(r)
                    expert_outputs.append(r)
                    discussion.append({
                        "round": round_num, "expertName": r["expert_name"],
                        "expertRole": r["expert_role"], "content": r["output"],
                        "timestamp": datetime.now().isoformat(),
                    })

                # PM 评估
                evaluation, eval_tokens = await _pm_evaluate(round_results, round_num)
                total_tokens += eval_tokens
                discussion.append({
                    "round": round_num, "expertName": leader.member_name,
                    "expertRole": "PM/组长(评估)", "content": json.dumps(evaluation, ensure_ascii=False),
                    "timestamp": datetime.now().isoformat(),
                })

                passed = evaluation.get("overall_pass", False)
                if passed:
                    break

                # 不达标：构建 feedback_map，继续下一轮
                if round_num < max_rounds:
                    feedback_map = {}
                    for score in evaluation.get("scores", []):
                        eid = score.get("expert_id")
                        fb = score.get("feedback", "")
                        if eid and fb:
                            feedback_map[eid] = fb
                    logger.info(f"[execute_team] 第 {round_num} 轮未达标，返工 feedback: {list(feedback_map.keys())}")

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # Step 5: PM 汇总最终报告
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            if not synthesizer_prompt:
                synthesizer_prompt = "请综合所有专家的分析结果，生成结构化的最终报告，包含：核心结论、各专家观点摘要、关键建议。"

            final_results_text = "\n\n".join([
                f"### {o['expert_name']}({o['expert_role']}) 第{o.get('round', '?')}轮 — {o['subtask']}\n{o['output']}"
                for o in expert_outputs if o["status"] == "done"
            ])

            report_prompt = f"""{pm_system}

## 用户原始任务
{request.input_text}

## 专家分析结果（共 {len(all_round_results)} 条）
{final_results_text}

## 工作指令
{synthesizer_prompt}

请生成最终报告。"""

            report_content, report_tokens = await _call_llm(
                db, pm_provider_id, pm_model_name, report_prompt, temperature=pm_temperature,
            )
            total_tokens += report_tokens

            await _ws_broadcast(team_id, "expert_status", {
                "expertName": leader.member_name, "expertRole": "PM/组长",
                "status": "done", "round": -1, "runId": run.id,
            })
            await _ws_broadcast(team_id, "expert_progress", {
                "status": "completed", "runId": run.id, "output": report_content[:500],
            })
            if on_progress:
                await on_progress({"type": "pm_report", "content": report_content})

            # ── 汇总结果 ──
            end_time = datetime.now()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            actual_rounds = max(r.get("round", 0) for r in all_round_results) if all_round_results else 0

            result = {
                "runId": run.id, "status": 2, "output": report_content,
                "discussion": discussion, "rounds": actual_rounds,
                "tokenUsage": total_tokens, "durationMs": duration_ms,
            }

            await self.repo.update_run(db, run.id, {
                "run_status": 2, "output_text": report_content,
                "discussion_json": discussion, "round_count": actual_rounds,
                "token_usage": total_tokens, "started_at": run.created_at,
                "finished_at": end_time, "duration_ms": duration_ms,
            })

            return result

        except Exception as e:
            logger.error(f"专家团执行失败: {e}", exc_info=True)
            await self.repo.update_run(db, run.id, {
                "run_status": 3, "error_message": str(e)[:2048],
                "finished_at": datetime.now(),
            })
            raise

    @staticmethod
    def _parse_evaluation(eval_output: str) -> dict:
        """解析 PM 评估 JSON

        Returns:
            {"overall_pass": bool, "scores": [{"expert_id", "score", "feedback"}], "reason": str}
        """
        import re
        try:
            # 尝试直接 JSON 解析
            data = json.loads(eval_output.strip())
            return {
                "overall_pass": data.get("overall_pass", False),
                "scores": data.get("scores", []),
                "reason": data.get("reason", ""),
            }
        except (json.JSONDecodeError, AttributeError):
            pass

        # 降级：从文本中提取 JSON 块
        match = re.search(r'\{[\s\S]*"overall_pass"[\s\S]*\}', eval_output)
        if match:
            try:
                data = json.loads(match.group())
                return {
                    "overall_pass": data.get("overall_pass", False),
                    "scores": data.get("scores", []),
                    "reason": data.get("reason", ""),
                }
            except json.JSONDecodeError:
                pass

        # 最终降级：关键词判断
        lower = eval_output.lower()
        passed = '"overall_pass": true' in lower or '达标' in eval_output or '"pass"' in lower
        return {"overall_pass": passed, "scores": [], "reason": eval_output[:200]}

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
