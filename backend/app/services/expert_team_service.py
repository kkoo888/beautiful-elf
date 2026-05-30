"""专家团工作流 Service — 基于 LangGraph 的多专家协作编排

架构 (参照 langgraph_workflow_orch_worker.py):
  START → orchestrator → Send(expert_1) | Send(expert_2) | ... → synthesizer → END

LangGraph StateGraph 流程:
  1. orchestrator: 分析任务，制定执行计划
  2. experts (并行 via Send): 各专家从专业角度分析
  3. synthesizer: 汇总所有专家意见，生成最终报告

LLM 集成:
  - 从 MySQL settings 表读取 ollama.host / ollama.chat_model
  - 通过 OllamaClient 调用本地 Ollama 服务
  - 每个专家可配置独立的 model / temperature / max_tokens
"""
import json
import logging
import asyncio
import operator
from typing import List, Optional, Tuple, Annotated, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from langgraph.graph import StateGraph, START, END
from langgraph.types import Send
from typing import TypedDict

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


# ─── LangGraph State 类型定义 ─────────────────────────────

class OrchestratorState(TypedDict):
    """编排器全局状态"""
    input_text: str
    expert_list: str
    members_data: list  # 序列化的成员信息
    orchestrator_prompt: str
    synthesizer_prompt: str
    max_rounds: int
    current_round: int
    discussion: Annotated[list[dict], operator.add]  # 讨论记录（可累加）
    expert_results: Annotated[list[dict], operator.add]  # 专家结果（可累加）
    final_output: str
    total_tokens: int


class ExpertState(TypedDict):
    """单个专家的工作状态"""
    member: dict
    input_text: str
    discussion: list[dict]
    round_num: int


# ─── LangGraph 节点函数 ──────────────────────────────────

async def orchestrator_node(state: OrchestratorState) -> dict:
    """Orchestrator 节点: 分析任务，生成执行计划"""
    client = OllamaClient()
    expert_list = state["expert_list"]
    input_text = state["input_text"]
    orchestrator_prompt = state["orchestrator_prompt"]

    prompt = (orchestrator_prompt or DEFAULT_ORCHESTRATOR_PROMPT).format(
        expert_list=expert_list,
        input_text=input_text,
    )

    response = await client.chat(
        messages=[{"role": "system", "content": prompt}],
        temperature=0.3,
    )

    tokens = response.get("eval_count", 0)
    msg = {
        "round": 0,
        "expert_name": "编排器",
        "expert_role": "Orchestrator",
        "content": response["content"],
        "timestamp": datetime.now().isoformat(),
    }

    logger.info(f"编排器分析完成: {response['content'][:100]}...")

    return {
        "discussion": [msg],
        "total_tokens": tokens,
        "current_round": 0,
    }


def assign_experts(state: OrchestratorState) -> list[Send]:
    """Fan-out: 为每个启用的专家分配任务（LangGraph Send 并行）"""
    members = state["members_data"]
    current_round = state["current_round"] + 1
    max_rounds = state["max_rounds"]

    if current_round > max_rounds:
        return [Send("synthesizer", state)]

    sends = []
    for member in members:
        expert_state = {
            "member": member,
            "input_text": state["input_text"],
            "discussion": state["discussion"],
            "round_num": current_round,
        }
        sends.append(Send("expert_call", expert_state))

    return sends


async def expert_call_node(state: ExpertState) -> dict:
    """单个专家节点: 从专业角度分析问题"""
    client = OllamaClient()
    member = state["member"]
    input_text = state["input_text"]
    discussion = state["discussion"]
    round_num = state["round_num"]

    # 构建上下文
    prev_msgs = [d for d in discussion if d.get("round", 0) > 0]
    if prev_msgs:
        prev_text = "\n".join([
            f"[{d['expert_name']}({d['expert_role']}) 第{d['round']}轮]: {d['content']}"
            for d in prev_msgs
        ])
        context = f"原始问题: {input_text}\n\n以下是其他专家的意见，请参考并补充:\n{prev_text}"
    else:
        context = f"原始问题: {input_text}\n\n请从你的专业角度分析这个问题。"

    base_prompt = member.get("system_prompt") or f"你是{member['name']}，角色是{member['role']}。请从专业角度分析问题。"
    prompt = f"""{base_prompt}

当前是第{round_num}轮讨论。
{context}

请从你的专业角度，给出深入、具体的分析。要求:
1. 观点明确，论据充分
2. 如有不同意见，直接提出
3. 控制在 300-500 字以内"""

    model = member.get("model_name") or None
    temperature = (member.get("temperature") or 70) / 100

    try:
        response = await client.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=member.get("max_tokens", 2048),
            model=model,
        )
        content = response["content"]
        tokens = response.get("eval_count", 0)
    except Exception as e:
        logger.error(f"专家 {member['name']} 调用失败: {e}")
        content = f"[调用失败: {e}]"
        tokens = 0

    msg = {
        "round": round_num,
        "expert_name": member["name"],
        "expert_role": member["role"],
        "content": content,
        "timestamp": datetime.now().isoformat(),
    }

    return {
        "discussion": [msg],
        "expert_results": [msg],
        "total_tokens": tokens,
    }


async def synthesizer_node(state: OrchestratorState) -> dict:
    """Synthesizer 节点: 汇总所有专家意见，生成最终报告"""
    client = OllamaClient()
    input_text = state["input_text"]
    discussion = state["discussion"]
    synthesizer_prompt = state["synthesizer_prompt"]

    # 格式化讨论内容
    lines = []
    for d in discussion:
        lines.append(f"[第{d['round']}轮] {d['expert_name']}({d['expert_role']}):\n{d['content']}\n")
    discussion_text = "\n".join(lines)

    prompt = (synthesizer_prompt or DEFAULT_SYNTHESIZER_PROMPT).format(
        input_text=input_text,
        discussion=discussion_text,
    )

    response = await client.chat(
        messages=[{"role": "system", "content": prompt}],
        temperature=0.3,
    )

    tokens = response.get("eval_count", 0)

    return {
        "final_output": response["content"],
        "total_tokens": tokens,
    }


# ─── 构建 LangGraph 工作流 ──────────────────────────────

def _build_expert_workflow():
    """构建 LangGraph StateGraph 工作流"""
    workflow = StateGraph(OrchestratorState)

    workflow.add_node("orchestrator", orchestrator_node)
    workflow.add_node("expert_call", expert_call_node)
    workflow.add_node("synthesizer", synthesizer_node)

    workflow.add_edge(START, "orchestrator")
    workflow.add_conditional_edges("orchestrator", assign_experts, ["expert_call", "synthesizer"])
    workflow.add_edge("expert_call", synthesizer_node)  # 单个专家完成后直接到 synthesizer
    workflow.add_edge("synthesizer", END)

    return workflow.compile()


# 编译一次，复用
_expert_graph = None


def get_expert_graph():
    global _expert_graph
    if _expert_graph is None:
        _expert_graph = _build_expert_workflow()
    return _expert_graph


# ─── 共识检测 ───────────────────────────────────────────

CONSENSUS_KEYWORDS = ["同意", "赞同", "一致", "共识", "没有异议", "完全同意"]


def _check_consensus(round_discussion: list) -> bool:
    """检查是否达成共识"""
    positive_count = sum(
        1 for d in round_discussion
        if any(kw in d["content"] for kw in CONSENSUS_KEYWORDS)
    )
    return positive_count >= len(round_discussion) * 0.7


# ─── Service 主类 ────────────────────────────────────────

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
            member_data = m.model_dump(by_alias=False)
            member_data["team_id"] = team.id
            member_data["sort_order"] = i
            member = await self.repo.create_member(db, member_data)
            members.append(member)

        return self._serialize_team(team, members)

    async def get_team_by_id(self, db: AsyncSession, team_id: int) -> dict:
        team = await self.repo.find_team_by_id(db, team_id)
        if not team:
            raise RecordNotFoundError("专家团不存在")
        members = await self.repo.find_members_by_team(db, team_id)
        return self._serialize_team(team, members)

    async def list_teams(
        self, db: AsyncSession, page: int = 1, page_size: int = 20,
        category: Optional[str] = None, enabled: Optional[int] = None,
    ) -> Tuple[list, int]:
        offset = (page - 1) * page_size
        teams = await self.repo.find_all_teams(db, offset=offset, limit=page_size, category=category, enabled=enabled)
        total = await self.repo.count_teams(db, category=category, enabled=enabled)

        # 批量查询成员（消除 N+1）
        team_ids = [t.id for t in teams]
        all_members = await self.repo.find_members_by_teams(db, team_ids)
        members_by_team: dict[int, list] = {}
        for m in all_members:
            members_by_team.setdefault(m.team_id, []).append(m)

        result = [self._serialize_team(t, members_by_team.get(t.id, [])) for t in teams]
        return result, total

    async def update_team(self, db: AsyncSession, team_id: int, data: ExpertTeamUpdate) -> dict:
        team = await self.repo.find_team_by_id(db, team_id)
        if not team:
            raise RecordNotFoundError("专家团不存在")
        update_data = data.model_dump(exclude_unset=True, by_alias=False)
        if update_data:
            team = await self.repo.update_team(db, team_id, update_data)
        members = await self.repo.find_members_by_team(db, team_id)
        return self._serialize_team(team, members)

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
        member_data = data.model_dump(by_alias=False)
        member_data["team_id"] = team_id
        member = await self.repo.create_member(db, member_data)
        return self._serialize_member(member)

    async def update_member(self, db: AsyncSession, member_id: int, data: dict) -> dict:
        member = await self.repo.find_member_by_id(db, member_id)
        if not member:
            raise RecordNotFoundError("专家成员不存在")
        member = await self.repo.update_member(db, member_id, data)
        return self._serialize_member(member)

    async def delete_member(self, db: AsyncSession, member_id: int) -> bool:
        member = await self.repo.find_member_by_id(db, member_id)
        if not member:
            raise RecordNotFoundError("专家成员不存在")
        return await self.repo.soft_delete_member(db, member_id)

    # ─── 执行专家团（LangGraph 核心）──────────────────

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

        start_time = datetime.now()

        try:
            # 序列化成员信息供 LangGraph 使用
            members_data = [self._serialize_member(m) for m in enabled_members]
            expert_list = ", ".join([f"{m['name']}({m['role']})" for m in members_data])

            # 构建 LangGraph 初始状态
            initial_state: OrchestratorState = {
                "input_text": request.input_text,
                "expert_list": expert_list,
                "members_data": members_data,
                "orchestrator_prompt": team.orchestrator_prompt or "",
                "synthesizer_prompt": team.synthesizer_prompt or "",
                "max_rounds": max_rounds,
                "current_round": 0,
                "discussion": [],
                "expert_results": [],
                "final_output": "",
                "total_tokens": 0,
            }

            # 执行 LangGraph 工作流
            graph = get_expert_graph()
            final_state = await graph.ainvoke(initial_state)

            end_time = datetime.now()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)

            # 计算实际轮次
            rounds = max(1, len(set(
                d["round"] for d in final_state.get("discussion", []) if d.get("round", 0) > 0
            )))

            result = {
                "run_id": run.id,
                "status": 2,
                "output": final_state["final_output"],
                "discussion": final_state.get("discussion", []),
                "rounds": rounds,
                "token_usage": final_state.get("total_tokens", 0),
                "duration_ms": duration_ms,
            }

            # 更新运行记录
            await self.repo.update_run(db, run.id, {
                "status": 2,  # 已完成
                "output_text": result["output"],
                "discussion_json": result["discussion"],
                "round_count": rounds,
                "token_usage": result["token_usage"],
                "started_at": run.created_at,
                "finished_at": end_time,
                "duration_ms": duration_ms,
            })

            return result

        except Exception as e:
            logger.error(f"专家团执行失败: {e}", exc_info=True)
            await self.repo.update_run(db, run.id, {
                "status": 3,  # 失败
                "error_message": str(e)[:2048],
                "finished_at": datetime.now(),
            })
            raise

    # ─── 运行记录查询 ──────────────────────────────────

    async def get_run_by_id(self, db: AsyncSession, run_id: int) -> dict:
        run = await self.repo.find_run_by_id(db, run_id)
        if not run:
            raise RecordNotFoundError("运行记录不存在")
        return self._serialize_run(run)

    async def list_runs_by_team(
        self, db: AsyncSession, team_id: int, page: int = 1, page_size: int = 20,
    ) -> Tuple[list, int]:
        offset = (page - 1) * page_size
        runs = await self.repo.find_runs_by_team(db, team_id, offset=offset, limit=page_size)
        total = await self.repo.count_runs_by_team(db, team_id)
        return [self._serialize_run(r) for r in runs], total

    async def list_all_runs(
        self, db: AsyncSession, page: int = 1, page_size: int = 20, status: Optional[int] = None,
    ) -> Tuple[list, int]:
        offset = (page - 1) * page_size
        runs = await self.repo.find_all_runs(db, offset=offset, limit=page_size, status=status)
        total = await self.repo.count_all_runs(db, status=status)
        return [self._serialize_run(r) for r in runs], total

    # ─── Pydantic 序列化（替代手动 dict）──────────────

    @staticmethod
    def _serialize_team(team, members=None) -> dict:
        """用 Pydantic schema 序列化专家团"""
        team_dict = ExpertTeamOut.model_validate(team).model_dump(by_alias=False)
        team_dict["members"] = [
            ExpertTeamOut.__annotations__  # placeholder
        ]
        # 直接构建，因为 members 需要单独处理
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
            "members": [ExpertTeamService._serialize_member(m) for m in (members or [])],
            "created_at": str(team.created_at) if team.created_at else None,
            "updated_at": str(team.updated_at) if team.updated_at else None,
        }

    @staticmethod
    def _serialize_member(member) -> dict:
        """用 Pydantic schema 序列化成员"""
        return ExpertMemberOut.model_validate(member).model_dump(by_alias=False)

    @staticmethod
    def _serialize_run(run) -> dict:
        """用 Pydantic schema 序列化运行记录"""
        return ExpertTeamRunOut.model_validate(run).model_dump(by_alias=False)
