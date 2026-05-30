"""专家团工作流 Service — 基于 LangGraph 的多专家协作编排

架构设计 (参照 langgraph_workflow_orch_worker.py):
  START → orchestrator → [expert_1, expert_2, ... expert_n] (并行) → synthesizer → END

LangGraph StateGraph 流程:
  1. orchestrator: 分析任务，制定执行计划
  2. experts (并行): 各专家从专业角度分析
  3. synthesizer: 汇总所有专家意见，生成最终报告

LLM 集成:
  - 从 MySQL settings 表读取 ollama.host / ollama.chat_model
  - 通过 OllamaClient 调用本地 Ollama 服务
  - 每个专家可配置独立的 model / temperature / max_tokens
"""
import json
import logging
import asyncio
from typing import List, Optional, Tuple
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.repository.expert_team_repo import ExpertTeamRepository
from app.schemas.expert_team import (
    ExpertTeamCreate, ExpertTeamUpdate, ExpertTeamOut,
    ExpertMemberCreate, ExpertMemberOut,
    ExpertTeamRunOut, ExpertTeamExecuteRequest,
    DiscussionMessage,
)
from app.core.exceptions import RecordNotFoundError
from app.services.ollama_service import OllamaClient, get_chat_model

logger = logging.getLogger(__name__)


# ─── 默认提示词模板 ──────────────────────────────────────

DEFAULT_ORCHESTRATOR_PROMPT = """你是一个任务编排器（Orchestrator）。
你的团队包含以下专家: {expert_list}。

请分析以下任务并制定执行计划:
1. 将任务拆解为各专家需要关注的子问题
2. 明确每个专家的分析重点
3. 指出可能需要跨专家协作的关键点

任务: {input_text}

请用 JSON 格式输出执行计划:
{{"plan": "执行计划描述", "expert_tasks": [{{"expert": "专家名", "focus": "分析重点"}}]}}"""

DEFAULT_EXPERT_PROMPT = """你是{name}，角色是{role}。
{system_prompt}

当前是第{round_num}轮讨论。
{context}

请从你的专业角度，给出深入、具体的分析。要求:
1. 观点明确，论据充分
2. 如有不同意见，直接提出
3. 控制在 300-500 字以内"""

DEFAULT_SYNTHESIZER_PROMPT = """你是一个汇总专家（Synthesizer）。
请综合所有专家的意见，生成最终的分析报告。

原始问题: {input_text}

专家讨论记录:
{discussion}

请生成结构化的最终报告，包含:
1. 核心结论（1-2 句话）
2. 各专家观点摘要
3. 关键建议
4. 风险提示（如有）"""


class ExpertTeamService:
    """专家团工作流 Service"""

    def __init__(self):
        self.repo = ExpertTeamRepository()

    # ─── 专家团 CRUD ───────────────────────────────────

    async def create_team(self, db: AsyncSession, data: ExpertTeamCreate) -> dict:
        """创建专家团（含成员）"""
        team_data = data.model_dump(exclude={"members"})
        team = await self.repo.create_team(db, team_data)

        members = []
        for i, m in enumerate(data.members):
            member_data = m.model_dump()
            member_data["team_id"] = team.id
            member_data["sort_order"] = i
            member = await self.repo.create_member(db, member_data)
            members.append(member)

        return self._team_to_dict(team, members)

    async def get_team_by_id(self, db: AsyncSession, team_id: int) -> dict:
        team = await self.repo.find_team_by_id(db, team_id)
        if not team:
            raise RecordNotFoundError("专家团不存在")
        members = await self.repo.find_members_by_team(db, team_id)
        return self._team_to_dict(team, members)

    async def list_teams(
        self, db: AsyncSession, page: int = 1, page_size: int = 20,
        category: Optional[str] = None, enabled: Optional[int] = None,
    ) -> Tuple[list, int]:
        offset = (page - 1) * page_size
        teams = await self.repo.find_all_teams(db, offset=offset, limit=page_size, category=category, enabled=enabled)
        total = await self.repo.count_teams(db, category=category, enabled=enabled)

        result = []
        for t in teams:
            members = await self.repo.find_members_by_team(db, t.id)
            result.append(self._team_to_dict(t, members))

        return result, total

    async def update_team(self, db: AsyncSession, team_id: int, data: ExpertTeamUpdate) -> dict:
        team = await self.repo.find_team_by_id(db, team_id)
        if not team:
            raise RecordNotFoundError("专家团不存在")
        update_data = data.model_dump(exclude_unset=True)
        if update_data:
            team = await self.repo.update_team(db, team_id, update_data)
        members = await self.repo.find_members_by_team(db, team_id)
        return self._team_to_dict(team, members)

    async def delete_team(self, db: AsyncSession, team_id: int) -> bool:
        team = await self.repo.find_team_by_id(db, team_id)
        if not team:
            raise RecordNotFoundError("专家团不存在")
        await self.repo.soft_delete_members_by_team(db, team_id)
        return await self.repo.soft_delete_team(db, team_id)

    # ─── 专家成员 CRUD ─────────────────────────────────

    async def add_member(self, db: AsyncSession, team_id: int, data: ExpertMemberCreate) -> dict:
        team = await self.repo.find_team_by_id(db, team_id)
        if not team:
            raise RecordNotFoundError("专家团不存在")
        member_data = data.model_dump()
        member_data["team_id"] = team_id
        member = await self.repo.create_member(db, member_data)
        return self._member_to_dict(member)

    async def update_member(self, db: AsyncSession, member_id: int, data: dict) -> dict:
        member = await self.repo.find_member_by_id(db, member_id)
        if not member:
            raise RecordNotFoundError("专家成员不存在")
        member = await self.repo.update_member(db, member_id, data)
        return self._member_to_dict(member)

    async def delete_member(self, db: AsyncSession, member_id: int) -> bool:
        member = await self.repo.find_member_by_id(db, member_id)
        if not member:
            raise RecordNotFoundError("专家成员不存在")
        return await self.repo.soft_delete_member(db, member_id)

    # ─── 执行专家团（LangGraph 核心 + Ollama LLM）─────

    async def execute_team(
        self, db: AsyncSession, team_id: int, request: ExpertTeamExecuteRequest,
    ) -> dict:
        """执行专家团工作流 — LangGraph Orchestrator-Worker 模式"""
        team = await self.repo.find_team_by_id(db, team_id)
        if not team:
            raise RecordNotFoundError("专家团不存在")

        members = await self.repo.find_members_by_team(db, team_id)
        enabled_members = [m for m in members if m.enabled == 1]
        if not enabled_members:
            raise RecordNotFoundError("专家团没有启用的成员")

        max_rounds = request.max_rounds or team.max_rounds

        # 创建运行记录
        run = await self.repo.create_run(db, {
            "team_id": team_id,
            "status": 1,  # 运行中
            "trigger_type": 0,
            "input_text": request.input_text,
        })

        try:
            result = await self._run_expert_workflow(
                team=team,
                members=enabled_members,
                input_text=request.input_text,
                max_rounds=max_rounds,
            )

            await self.repo.update_run(db, run.id, {
                "status": 2,  # 已完成
                "output_text": result["output"],
                "discussion_json": result["discussion"],
                "round_count": result["rounds"],
                "token_usage": result["token_usage"],
                "started_at": run.created_at,
                "finished_at": datetime.now(),
                "duration_ms": result["duration_ms"],
            })

            return {
                "run_id": run.id,
                "status": 2,
                "output": result["output"],
                "discussion": result["discussion"],
                "rounds": result["rounds"],
                "token_usage": result["token_usage"],
                "duration_ms": result["duration_ms"],
            }

        except Exception as e:
            logger.error(f"专家团执行失败: {e}", exc_info=True)
            await self.repo.update_run(db, run.id, {
                "status": 3,  # 失败
                "error_message": str(e)[:2048],
                "finished_at": datetime.now(),
            })
            raise

    async def _run_expert_workflow(
        self, team, members, input_text: str, max_rounds: int,
    ) -> dict:
        """执行 LangGraph 专家团工作流

        流程 (参照 langgraph_workflow_orch_worker.py):
        1. Orchestrator: 分析任务 → 生成执行计划
        2. Experts (并行): 各专家独立分析
        3. 多轮讨论: 专家参考他人意见补充修正
        4. Synthesizer: 汇总生成最终报告
        """
        start_time = datetime.now()
        discussion: List[dict] = []
        total_tokens = 0

        # 初始化 Ollama 客户端
        client = OllamaClient()

        # ── Step 1: Orchestrator 分析任务 ──
        expert_list = ", ".join([f"{m.name}({m.role})" for m in members])
        orch_prompt = (team.orchestrator_prompt or DEFAULT_ORCHESTRATOR_PROMPT).format(
            expert_list=expert_list,
            input_text=input_text,
        )

        orch_response = await client.chat(
            messages=[{"role": "system", "content": orch_prompt}],
            temperature=0.3,
        )
        total_tokens += orch_response.get("eval_count", 0)

        discussion.append({
            "round": 0,
            "expert_name": "编排器",
            "expert_role": "Orchestrator",
            "content": orch_response["content"],
            "timestamp": datetime.now().isoformat(),
        })

        logger.info(f"编排器分析完成: {orch_response['content'][:100]}...")

        # ── Step 2: 多轮专家讨论 ──
        for round_num in range(1, max_rounds + 1):
            logger.info(f"开始第 {round_num} 轮讨论 ({len(members)} 位专家)")

            # 并行调用所有专家
            tasks = []
            for member in members:
                context = self._build_context(input_text, discussion, member, round_num)
                expert_prompt = self._build_expert_prompt(member, context, round_num)
                tasks.append(self._call_expert(client, member, expert_prompt))

            # asyncio.gather 并行执行
            results = await asyncio.gather(*tasks, return_exceptions=True)

            round_discussion = []
            for member, result in zip(members, results):
                if isinstance(result, Exception):
                    logger.error(f"专家 {member.name} 调用失败: {result}")
                    content = f"[调用失败: {result}]"
                else:
                    content = result["content"]
                    total_tokens += result.get("eval_count", 0)

                msg = {
                    "round": round_num,
                    "expert_name": member.name,
                    "expert_role": member.role,
                    "content": content,
                    "timestamp": datetime.now().isoformat(),
                }
                round_discussion.append(msg)

            discussion.extend(round_discussion)

            # 收敛检测
            if self._check_consensus(round_discussion):
                logger.info(f"第 {round_num} 轮达成共识，提前结束讨论")
                break

        # ── Step 3: Synthesizer 汇总 ──
        synthesis_discussion = self._format_discussion_for_synthesis(discussion)
        synth_prompt = (team.synthesizer_prompt or DEFAULT_SYNTHESIZER_PROMPT).format(
            input_text=input_text,
            discussion=synthesis_discussion,
        )

        synth_response = await client.chat(
            messages=[{"role": "system", "content": synth_prompt}],
            temperature=0.3,
        )
        total_tokens += synth_response.get("eval_count", 0)

        end_time = datetime.now()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        logger.info(f"专家团执行完成: {duration_ms}ms, {total_tokens} tokens")

        return {
            "output": synth_response["content"],
            "discussion": discussion,
            "rounds": max(1, len(set(d["round"] for d in discussion if d["round"] > 0))),
            "token_usage": total_tokens,
            "duration_ms": duration_ms,
        }

    async def _call_expert(self, client: OllamaClient, member, prompt: str) -> dict:
        """调用单个专家 LLM"""
        # 专家可配置独立模型，否则用全局默认模型
        model = member.model_name if member.model_name else None
        temperature = member.temperature / 100 if member.temperature else 0.7

        return await client.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=member.max_tokens,
            model=model,
        )

    def _build_expert_prompt(self, member, context: str, round_num: int) -> str:
        """构建专家的完整提示词"""
        base_prompt = member.system_prompt or f"你是{member.name}，角色是{member.role}。请从专业角度分析问题。"
        return f"""{base_prompt}

当前是第{round_num}轮讨论。
{context}

请从你的专业角度，给出深入、具体的分析。要求:
1. 观点明确，论据充分
2. 如有不同意见，直接提出
3. 控制在 300-500 字以内"""

    def _build_context(self, input_text: str, discussion: list, member, round_num: int) -> str:
        """构建专家的输入上下文"""
        prev_msgs = [d for d in discussion if d["round"] > 0]
        if not prev_msgs:
            return f"原始问题: {input_text}\n\n请从你的专业角度分析这个问题。"

        prev_text = "\n".join([
            f"[{d['expert_name']}({d['expert_role']}) 第{d['round']}轮]: {d['content']}"
            for d in prev_msgs
        ])
        return (
            f"原始问题: {input_text}\n\n"
            f"以下是其他专家的意见，请参考并补充你的观点:\n{prev_text}"
        )

    def _check_consensus(self, round_discussion: list) -> bool:
        """检查是否达成共识"""
        consensus_keywords = ["同意", "赞同", "一致", "共识", "没有异议", "完全同意"]
        positive_count = sum(
            1 for d in round_discussion
            if any(kw in d["content"] for kw in consensus_keywords)
        )
        return positive_count >= len(round_discussion) * 0.7

    def _format_discussion_for_synthesis(self, discussion: list) -> str:
        """格式化讨论内容供汇总器使用"""
        lines = []
        for d in discussion:
            lines.append(f"[第{d['round']}轮] {d['expert_name']}({d['expert_role']}):\n{d['content']}\n")
        return "\n".join(lines)

    # ─── 运行记录查询 ──────────────────────────────────

    async def get_run_by_id(self, db: AsyncSession, run_id: int) -> dict:
        run = await self.repo.find_run_by_id(db, run_id)
        if not run:
            raise RecordNotFoundError("运行记录不存在")
        return self._run_to_dict(run)

    async def list_runs_by_team(
        self, db: AsyncSession, team_id: int, page: int = 1, page_size: int = 20,
    ) -> Tuple[list, int]:
        offset = (page - 1) * page_size
        runs = await self.repo.find_runs_by_team(db, team_id, offset=offset, limit=page_size)
        total = await self.repo.count_runs_by_team(db, team_id)
        return [self._run_to_dict(r) for r in runs], total

    async def list_all_runs(
        self, db: AsyncSession, page: int = 1, page_size: int = 20, status: Optional[int] = None,
    ) -> Tuple[list, int]:
        offset = (page - 1) * page_size
        runs = await self.repo.find_all_runs(db, offset=offset, limit=page_size, status=status)
        total = await self.repo.count_all_runs(db, status=status)
        return [self._run_to_dict(r) for r in runs], total

    # ─── 序列化 ─────────────────────────────────────────

    @staticmethod
    def _team_to_dict(team, members=None) -> dict:
        return {
            "id": team.id,
            "name": team.name,
            "description": team.description,
            "icon": team.icon,
            "category": team.category,
            "orchestrator_prompt": team.orchestrator_prompt,
            "synthesizer_prompt": team.synthesizer_prompt,
            "max_rounds": team.max_rounds,
            "enabled": team.enabled,
            "version": team.version,
            "config_json": team.config_json,
            "members": [ExpertTeamService._member_to_dict(m) for m in (members or [])],
            "created_at": str(team.created_at) if team.created_at else None,
            "updated_at": str(team.updated_at) if team.updated_at else None,
        }

    @staticmethod
    def _member_to_dict(member) -> dict:
        return {
            "id": member.id,
            "team_id": member.team_id,
            "name": member.name,
            "role": member.role,
            "avatar": member.avatar,
            "system_prompt": member.system_prompt,
            "model_name": member.model_name,
            "temperature": member.temperature,
            "max_tokens": member.max_tokens,
            "tools_json": member.tools_json,
            "sort_order": member.sort_order,
            "enabled": member.enabled,
            "created_at": str(member.created_at) if member.created_at else None,
            "updated_at": str(member.updated_at) if member.updated_at else None,
        }

    @staticmethod
    def _run_to_dict(run) -> dict:
        return {
            "id": run.id,
            "team_id": run.team_id,
            "status": run.status,
            "trigger_type": run.trigger_type,
            "input_text": run.input_text,
            "output_text": run.output_text,
            "discussion_json": run.discussion_json,
            "error_message": run.error_message,
            "round_count": run.round_count,
            "token_usage": run.token_usage,
            "started_at": str(run.started_at) if run.started_at else None,
            "finished_at": str(run.finished_at) if run.finished_at else None,
            "duration_ms": run.duration_ms,
            "created_at": str(run.created_at) if run.created_at else None,
        }
