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

WebSocket 实时推送:
  - expert_status: 专家状态变更（开始/完成/失败）
  - expert_thinking: 专家推理过程
  - expert_progress: 任务进度更新
"""
import json
import logging
import asyncio
import operator
import uuid
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
    RoleSkillCreate, RoleSkillUpdate, RoleSkillOut, ExpertRoleRunOut,
)
from app.core.exceptions import RecordNotFoundError
from app.services.ollama_service import OllamaClient, get_chat_model

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
    members_data: list  # 序列化的成员信息 (含 skills)
    orchestrator_prompt: str
    synthesizer_prompt: str
    max_rounds: int
    current_round: int
    discussion: Annotated[list[dict], operator.add]  # 讨论记录（可累加）
    expert_results: Annotated[list[dict], operator.add]  # 专家结果（可累加）
    role_run_ids: Annotated[list[dict], operator.add]  # 角色执行记录 ID（可累加）
    final_output: str
    total_tokens: int
    run_id: int  # 专家团运行记录 ID
    _service: Any  # service 实例引用
    _db: Any  # db session 引用
    _team_id: int  # 专家团 ID（WebSocket 推送用）


class ExpertState(TypedDict):
    """单个专家的工作状态"""
    member: dict
    input_text: str
    discussion: list[dict]
    round_num: int
    run_id: int
    _service: Any
    _db: Any
    _team_id: int  # 专家团 ID（WebSocket 推送用）


# ─── LangGraph 节点函数 ──────────────────────────────────

CONSENSUS_KEYWORDS = ["同意", "赞同", "一致", "共识", "没有异议", "完全同意"]


def _check_consensus(round_discussion: list) -> bool:
    """检查是否达成共识"""
    positive_count = sum(
        1 for d in round_discussion
        if any(kw in d["content"] for kw in CONSENSUS_KEYWORDS)
    )
    return positive_count >= len(round_discussion) * 0.7


async def orchestrator_node(state: OrchestratorState) -> dict:
    """Orchestrator 节点: 分析任务，生成执行计划（第一轮才执行）"""
    client = OllamaClient()
    expert_list = state["expert_list"]
    input_text = state["input_text"]
    orchestrator_prompt = state["orchestrator_prompt"]
    current_round = state.get("current_round", 0)
    team_id = state.get("_team_id", 0)

    # 第一轮：分析任务
    if current_round == 0:
        # 推送：编排器开始分析
        await _ws_broadcast(team_id, "expert_status", {
            "expertName": "编排器",
            "expertRole": "Orchestrator",
            "status": "running",
            "round": 0,
            "runId": state.get("run_id"),
        })

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
            "expertName": "编排器",
            "expertRole": "Orchestrator",
            "content": response["content"],
            "timestamp": datetime.now().isoformat(),
        }
        logger.info(f"编排器分析完成: {response['content'][:100]}...")

        # 推送：编排器完成 + 推理内容
        await _ws_broadcast(team_id, "expert_thinking", {
            "expertName": "编排器",
            "expertRole": "Orchestrator",
            "round": 0,
            "content": response["content"],
            "runId": state.get("run_id"),
        })
        await _ws_broadcast(team_id, "expert_status", {
            "expertName": "编排器",
            "expertRole": "Orchestrator",
            "status": "done",
            "round": 0,
            "runId": state.get("run_id"),
        })

        return {
            "discussion": [msg],
            "total_tokens": tokens,
            "current_round": 1,
        }

    # 后续轮次：跳过编排器，直接进入专家讨论
    return {"current_round": current_round + 1}


def route_after_orchestrator(state: OrchestratorState) -> list[Send]:
    """编排器之后: 判断是继续讨论还是汇总

    LangGraph Send 并行分发: 为每位专家创建独立分支
    """
    current_round = state["current_round"]
    max_rounds = state["max_rounds"]
    discussion = state.get("discussion", [])

    # 检查是否应该结束讨论
    if current_round > max_rounds:
        return [Send("synthesizer", state)]

    # 检查上一轮是否达成共识（跳过 round 0 编排器）
    prev_round_msgs = [d for d in discussion if d.get("round", 0) == current_round - 1 and d.get("round", 0) > 0]
    if prev_round_msgs and _check_consensus(prev_round_msgs):
        logger.info(f"第 {current_round - 1} 轮达成共识，提前进入汇总")
        return [Send("synthesizer", state)]

    # Fan-out: 为每位专家分发任务
    sends = []
    for member in state["members_data"]:
        expert_state: ExpertState = {
            "member": member,
            "input_text": state["input_text"],
            "discussion": state["discussion"],
            "round_num": current_round,
            "run_id": state["run_id"],
            "_service": state["_service"],
            "_db": state["_db"],
            "_team_id": state.get("_team_id", 0),
        }
        sends.append(Send("expert_call", expert_state))

    return sends


async def expert_call_node(state: ExpertState) -> dict:
    """单个专家节点: 从专业角度分析问题，追踪角色执行记录"""
    client = OllamaClient()
    member = state["member"]
    input_text = state["input_text"]
    discussion = state["discussion"]
    round_num = state["round_num"]
    run_id = state["run_id"]
    service = state["_service"]
    db = state["_db"]
    team_id = state.get("_team_id", 0)

    # 推送：专家开始工作
    await _ws_broadcast(team_id, "expert_status", {
        "expertName": member["name"],
        "expertRole": member["role"],
        "avatar": member.get("avatar", "🤖"),
        "status": "running",
        "round": round_num,
        "runId": run_id,
    })

    # 创建角色执行记录
    role_run = await service._create_role_run(db, run_id, member["id"], member["name"], round_num)

    # 构建上下文
    prev_msgs = [d for d in discussion if d.get("round", 0) > 0]
    if prev_msgs:
        prev_text = "\n".join([
            f"[{d['expertName']}({d['expertRole']}) 第{d['round']}轮]: {d['content']}"
            for d in prev_msgs
        ])
        context = f"原始问题: {input_text}\n\n以下是其他专家的意见，请参考并补充:\n{prev_text}"
    else:
        context = f"原始问题: {input_text}\n\n请从你的专业角度分析这个问题。"

    base_prompt = member.get("system_prompt") or f"你是{member['name']}，角色是{member['role']}。请从专业角度分析问题。"

    # 构建技能上下文
    skills = member.get("skills", [])
    skill_context = ""
    skills_used = []
    if skills:
        skill_names = ", ".join([s.get("display_name", s.get("name", "")) for s in skills])
        skill_context = f"\n\n你可以使用以下技能来辅助分析: {skill_names}"

    prompt = f"""{base_prompt}

当前是第{round_num}轮讨论。
{context}{skill_context}

请从你的专业角度，给出深入、具体的分析。要求:
1. 观点明确，论据充分
2. 如有不同意见，直接提出
3. 控制在 300-500 字以内"""

    model = member.get("model_name") or None
    temperature = (member.get("temperature") or 70) / 100

    start_time = datetime.now()
    try:
        response = await client.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=member.get("max_tokens", 2048),
            model=model,
        )
        content = response["content"]
        tokens = response.get("eval_count", 0)

        # 完成角色执行记录
        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        await service._finish_role_run(
            db, role_run.id, status=2,
            output=content, skills_used=skills_used, tokens=tokens,
        )

    except Exception as e:
        logger.error(f"专家 {member['name']} 调用失败: {e}")
        content = f"[调用失败: {e}]"
        tokens = 0
        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        await service._finish_role_run(
            db, role_run.id, status=3,
            error=str(e),
        )

        # 推送：专家失败
        await _ws_broadcast(team_id, "expert_status", {
            "expertName": member["name"],
            "expertRole": member["role"],
            "avatar": member.get("avatar", "🤖"),
            "status": "failed",
            "round": round_num,
            "runId": run_id,
            "error": str(e),
        })

    msg = {
        "round": round_num,
        "expertName": member["name"],
        "expertRole": member["role"],
        "content": content,
        "timestamp": datetime.now().isoformat(),
    }

    # 推送：专家推理内容
    await _ws_broadcast(team_id, "expert_thinking", {
        "expertName": member["name"],
        "expertRole": member["role"],
        "avatar": member.get("avatar", "🤖"),
        "round": round_num,
        "content": content,
        "runId": run_id,
        "durationMs": duration_ms,
    })

    # 推送：专家完成
    await _ws_broadcast(team_id, "expert_status", {
        "expertName": member["name"],
        "expertRole": member["role"],
        "avatar": member.get("avatar", "🤖"),
        "status": "done",
        "round": round_num,
        "runId": run_id,
        "durationMs": duration_ms,
    })

    return {
        "discussion": [msg],
        "expert_results": [msg],
        "total_tokens": tokens,
        "role_run_ids": [{"role_id": member["id"], "role_run_id": role_run.id}],
    }


async def synthesizer_node(state: OrchestratorState) -> dict:
    """Synthesizer 节点: 汇总所有专家意见，生成最终报告"""
    client = OllamaClient()
    input_text = state["input_text"]
    discussion = state["discussion"]
    synthesizer_prompt = state["synthesizer_prompt"]
    team_id = state.get("_team_id", 0)

    # 推送：汇总器开始
    await _ws_broadcast(team_id, "expert_status", {
        "expertName": "汇总器",
        "expertRole": "Synthesizer",
        "status": "running",
        "round": -1,
        "runId": state.get("run_id"),
    })

    # 格式化讨论内容
    lines = []
    for d in discussion:
        lines.append(f"[第{d['round']}轮] {d['expertName']}({d['expertRole']}):\n{d['content']}\n")
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

    # 推送：汇总器完成
    await _ws_broadcast(team_id, "expert_status", {
        "expertName": "汇总器",
        "expertRole": "Synthesizer",
        "status": "done",
        "round": -1,
        "runId": state.get("run_id"),
    })
    await _ws_broadcast(team_id, "expert_progress", {
        "status": "completed",
        "runId": state.get("run_id"),
        "output": response["content"][:500],
    })

    return {
        "final_output": response["content"],
        "total_tokens": tokens,
    }


async def round_router_node(state: OrchestratorState) -> dict:
    """路由节点: 专家讨论结束后，递增轮次计数器"""
    return {"current_round": state["current_round"] + 1}


def route_after_round(state: OrchestratorState) -> list[Send]:
    """专家讨论结束后: 判断是继续下一轮还是汇总"""
    current_round = state["current_round"]
    max_rounds = state["max_rounds"]
    discussion = state.get("discussion", [])

    # 检查是否应该结束讨论
    if current_round >= max_rounds:
        return [Send("synthesizer", state)]

    # 检查当前轮是否达成共识
    current_round_msgs = [d for d in discussion if d.get("round", 0) == current_round]
    if current_round_msgs and _check_consensus(current_round_msgs):
        logger.info(f"第 {current_round} 轮达成共识，提前进入汇总")
        return [Send("synthesizer", state)]

    # Fan-out: 下一轮专家讨论
    next_round = current_round + 1
    sends = []
    for member in state["members_data"]:
        expert_state: ExpertState = {
            "member": member,
            "input_text": state["input_text"],
            "discussion": state["discussion"],
            "round_num": next_round,
            "run_id": state["run_id"],
            "_service": state["_service"],
            "_db": state["_db"],
            "_team_id": state.get("_team_id", 0),
        }
        sends.append(Send("expert_call", expert_state))

    return sends


# ─── 构建 LangGraph 工作流 ──────────────────────────────

def _build_expert_workflow():
    """构建 LangGraph StateGraph 工作流

    流程:
      START → orchestrator → [Send(expert_1), Send(expert_2), ...] → round_router
        → (检查共识/轮次) → [Send(expert_1), ...] 或 → synthesizer → END

    使用 LangGraph Send API 实现动态并行分发
    """
    workflow = StateGraph(OrchestratorState)

    workflow.add_node("orchestrator", orchestrator_node)
    workflow.add_node("expert_call", expert_call_node)
    workflow.add_node("round_router", round_router_node)
    workflow.add_node("synthesizer", synthesizer_node)

    # START → orchestrator
    workflow.add_edge(START, "orchestrator")

    # orchestrator → Send(experts) 或 Send(synthesizer)
    workflow.add_conditional_edges("orchestrator", route_after_orchestrator, ["expert_call", "synthesizer"])

    # experts 完成后 → round_router（等待所有专家完成，合并 discussion）
    workflow.add_edge("expert_call", "round_router")

    # round_router → 继续下一轮或汇总
    workflow.add_conditional_edges("round_router", route_after_round, ["expert_call", "synthesizer"])

    # synthesizer → END
    workflow.add_edge("synthesizer", END)

    return workflow.compile()


# 编译一次，复用
_expert_graph = None


def get_expert_graph():
    global _expert_graph
    if _expert_graph is None:
        _expert_graph = _build_expert_workflow()
    return _expert_graph


# ─── Service 主类 ────────────────────────────────────────

class ExpertTeamService:
    """专家团工作流 Service"""

    def __init__(self):
        self.repo = ExpertTeamRepository()

    # ─── 专家团 CRUD ───────────────────────────────────

    async def create_team(self, db: AsyncSession, data: ExpertTeamCreate) -> ExpertTeamOut:
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

        return self._to_out_team(team, members)

    async def get_team_by_id(self, db: AsyncSession, team_id: int) -> ExpertTeamOut:
        team = await self.repo.find_team_by_id(db, team_id)
        if not team:
            raise RecordNotFoundError("专家团不存在")
        members = await self.repo.find_members_by_team(db, team_id)
        return self._to_out_team(team, members)

    async def list_teams(
        self, db: AsyncSession, page: int = 1, page_size: int = 20,
        category: Optional[str] = None, enabled: Optional[int] = None,
    ) -> Tuple[List[ExpertTeamOut], int]:
        offset = (page - 1) * page_size
        teams = await self.repo.find_all_teams(db, offset=offset, limit=page_size, category=category, enabled=enabled)
        total = await self.repo.count_teams(db, category=category, enabled=enabled)

        # 批量查询成员（消除 N+1）
        team_ids = [t.id for t in teams]
        all_members = await self.repo.find_members_by_teams(db, team_ids)
        members_by_team: dict[int, list] = {}
        for m in all_members:
            members_by_team.setdefault(m.team_id, []).append(m)

        result = [self._to_out_team(t, members_by_team.get(t.id, [])) for t in teams]
        return result, total

    async def update_team(self, db: AsyncSession, team_id: int, data: ExpertTeamUpdate) -> ExpertTeamOut:
        team = await self.repo.find_team_by_id(db, team_id)
        if not team:
            raise RecordNotFoundError("专家团不存在")
        update_data = data.model_dump(exclude_unset=True, by_alias=False)
        # members 单独处理，不传给 repo.update_team
        members_data = update_data.pop("members", None)
        if update_data:
            team = await self.repo.update_team(db, team_id, update_data)
        # 同步成员：整体替换模式
        if members_data is not None:
            old_members = await self.repo.find_members_by_team(db, team_id)
            old_map = {m.id: m for m in old_members}
            new_members = []
            for i, m in enumerate(members_data):
                m["team_id"] = team_id
                m["sort_order"] = i
                if i < len(old_members):
                    # 更新已有成员
                    old = old_members[i]
                    await self.repo.update_member(db, old.id, m)
                    new_members.append(await self.repo.find_member_by_id(db, old.id))
                else:
                    # 新增成员
                    member = await self.repo.create_member(db, m)
                    new_members.append(member)
            # 删除多余成员
            for j in range(len(members_data), len(old_members)):
                await self.repo.soft_delete_member(db, old_members[j].id)
            return self._to_out_team(team, new_members)
        members = await self.repo.find_members_by_team(db, team_id)
        return self._to_out_team(team, members)

    async def delete_team(self, db: AsyncSession, team_id: int) -> bool:
        team = await self.repo.find_team_by_id(db, team_id)
        if not team:
            raise RecordNotFoundError("专家团不存在")
        await self.repo.soft_delete_members_by_team(db, team_id)
        return await self.repo.soft_delete_team(db, team_id)

    # ─── 专家成员 CRUD ─────────────────────────────────

    async def add_member(self, db: AsyncSession, team_id: int, data: ExpertMemberCreate) -> ExpertMemberOut:
        team = await self.repo.find_team_by_id(db, team_id)
        if not team:
            raise RecordNotFoundError("专家团不存在")
        member_data = data.model_dump(by_alias=False)
        member_data["team_id"] = team_id
        member = await self.repo.create_member(db, member_data)
        return self._to_out_member(member)

    async def update_member(self, db: AsyncSession, member_id: int, data: dict) -> ExpertMemberOut:
        member = await self.repo.find_member_by_id(db, member_id)
        if not member:
            raise RecordNotFoundError("专家成员不存在")
        member = await self.repo.update_member(db, member_id, data)
        return self._to_out_member(member)

    async def delete_member(self, db: AsyncSession, member_id: int) -> bool:
        member = await self.repo.find_member_by_id(db, member_id)
        if not member:
            raise RecordNotFoundError("专家成员不存在")
        return await self.repo.soft_delete_member(db, member_id)

    # ─── 角色技能绑定 ─────────────────────────────────

    async def list_member_skills(self, db: AsyncSession, member_id: int) -> list:
        """查询成员绑定的技能（含技能详情）"""
        binds = await self.repo.find_skills_by_role(db, member_id)
        result = []
        for b in binds:
            skill = await self._get_skill_info(db, b.skill_id)
            result.append({
                "id": b.id,
                "roleId": b.role_id,
                "skillId": b.skill_id,
                "skillName": skill.get("name", "") if skill else "",
                "skillDisplayName": skill.get("display_name", "") if skill else "",
                "skillDescription": skill.get("description", "") if skill else "",
                "priority": b.priority,
                "configOverride": b.config_override,
                "enabled": b.is_enabled,
                "createdAt": str(b.created_at) if b.created_at else None,
                "updatedAt": str(b.updated_at) if b.updated_at else None,
            })
        return result

    async def bind_skill(self, db: AsyncSession, member_id: int, data: RoleSkillCreate) -> RoleSkillOut:
        """绑定技能到成员"""
        member = await self.repo.find_member_by_id(db, member_id)
        if not member:
            raise RecordNotFoundError("专家成员不存在")
        bind_data = data.model_dump(by_alias=False)
        bind_data["role_id"] = member_id
        # 检查是否已绑定
        existing = await self.repo.find_skill_bind(db, member_id, data.skill_id)
        if existing:
            # 更新已有绑定
            bind = await self.repo.update_skill_bind(db, existing.id, bind_data)
        else:
            bind = await self.repo.create_skill_bind(db, bind_data)
        return self._to_out_skill_bind(bind)

    async def update_skill_bind(self, db: AsyncSession, bind_id: int, data: RoleSkillUpdate) -> RoleSkillOut:
        """更新角色技能绑定"""
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

    async def list_role_runs(self, db: AsyncSession, run_id: int) -> List[ExpertRoleRunOut]:
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

    def _to_out_skill_bind(self, bind) -> RoleSkillOut:
        return RoleSkillOut.model_validate(bind)

    def _to_out_role_run(self, run) -> ExpertRoleRunOut:
        return ExpertRoleRunOut.model_validate(run)

    # ─── 执行专家团（LangGraph 核心）──────────────────

    async def execute_team(
        self, db: AsyncSession, team_id: int, request: ExpertTeamExecuteRequest,
    ) -> dict:
        """执行专家团工作流 — LangGraph Orchestrator-Worker 模式"""
        team = await self.repo.find_team_by_id(db, team_id)
        if not team:
            raise RecordNotFoundError("专家团不存在")

        members = await self.repo.find_members_by_team(db, team_id)
        enabled_members = [m for m in members if m.is_enabled == 1]
        if not enabled_members:
            raise RecordNotFoundError("专家团没有启用的成员")

        max_rounds = request.max_rounds or team.max_rounds

        # 创建运行记录
        run = await self.repo.create_run(db, {
            "team_id": team_id,
            "run_status": 1,  # 运行中
            "trigger_type": 0,
            "input_text": request.input_text,
        })

        start_time = datetime.now()

        try:
            # 序列化成员信息供 LangGraph 使用（需要 dict 供 LangGraph state）
            members_data = [self._to_out_member(m).model_dump() for m in enabled_members]

            # 批量加载技能绑定（消除 N+1）
            member_ids = [m["id"] for m in members_data]
            all_skills = await self.repo.find_skills_by_roles(db, member_ids)
            skills_by_role: dict[int, list] = {}
            for s in all_skills:
                skills_by_role.setdefault(s.role_id, []).append(s)

            # 加载技能详情并注入到成员数据
            for m in members_data:
                binds = skills_by_role.get(m["id"], [])
                m["skills"] = []
                for b in binds:
                    skill_info = await self._get_skill_info(db, b.skill_id)
                    if skill_info:
                        skill_info["priority"] = b.priority
                        skill_info["config_override"] = b.config_override
                        m["skills"].append(skill_info)

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
                "role_run_ids": [],
                "final_output": "",
                "total_tokens": 0,
                "run_id": run.id,
                "_service": self,
                "_db": db,
                "_team_id": team_id,
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
                "runId": run.id,
                "status": 2,
                "output": final_state["final_output"],
                "discussion": final_state.get("discussion", []),
                "rounds": rounds,
                "tokenUsage": final_state.get("total_tokens", 0),
                "durationMs": duration_ms,
            }

            # 更新运行记录
            await self.repo.update_run(db, run.id, {
                "run_status": 2,  # 已完成
                "output_text": result["output"],
                "discussion_json": result["discussion"],
                "round_count": rounds,
                "token_usage": result["tokenUsage"],
                "started_at": run.created_at,
                "finished_at": end_time,
                "duration_ms": duration_ms,
            })

            return result

        except Exception as e:
            logger.error(f"专家团执行失败: {e}", exc_info=True)
            await self.repo.update_run(db, run.id, {
                "run_status": 3,  # 失败
                "error_message": str(e)[:2048],
                "finished_at": datetime.now(),
            })
            raise

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
    def _to_out_team(team, members=None) -> ExpertTeamOut:
        """序列化专家团"""
        team_out = ExpertTeamOut.model_validate(team)
        team_out.members = [ExpertTeamService._to_out_member(m) for m in (members or [])]
        return team_out

    @staticmethod
    def _to_out_member(member) -> ExpertMemberOut:
        """用 Pydantic schema 序列化成员"""
        return ExpertMemberOut.model_validate(member)

    @staticmethod
    def _to_out_run(run) -> ExpertTeamRunOut:
        """用 Pydantic schema 序列化运行记录"""
        return ExpertTeamRunOut.model_validate(run)
