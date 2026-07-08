"""行为分析引擎 — 方案 D + ProactiveAgent 借鉴

架构：
  Phase 1: SQL 聚合 — 从 action_log 提取高频动作 + 时间分布 + 动作序列
  Phase 2: 启发式规则 — 识别行为模式（每日习惯、连续动作、时间规律）
  Phase 3: LLM 分析 — 结构化输出 Purpose/Thoughts/Suggestion（ProactiveAgent 借鉴）

ProactiveAgent 核心借鉴：
  1. 结构化输出：先分析用户目的（Purpose），再思考（Thoughts），最后决定是否建议
  2. 允许 null：没有好建议时返回空，不硬凑
  3. 用户反馈循环：忽略 3 次以上 → 不再建议同类技能
  4. 模式已解决标记：已接受的模式标记 is_solved，不重复建议

触发方式：用户在意图学习页面手动点击「分析行为模式」按钮
"""
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_log import ActionLog
from app.models.intent_learning import BehaviorPattern, SkillSuggestion
from app.repository.intent_learning_repo import BehaviorPatternRepository, SkillSuggestionRepository
from app.core.logging import get_logger

logger = get_logger(__name__)

# ── 配置 ─────────────────────────────────────────────────

MIN_ACTION_COUNT = 5          # 最少出现次数才算高频
MIN_SEQUENCE_COUNT = 3        # 序列最少出现次数
MIN_PATTERN_FREQUENCY = 3     # 模式最少触发频率
ANALYSIS_DAYS = 7             # 分析最近 N 天的数据
MAX_PATTERNS = 20             # 最多生成 N 个模式
MAX_SUGGESTIONS = 5           # 最多生成 N 个建议
IGNORE_THRESHOLD = 3          # 连续忽略阈值

# 模块+动作的中文映射（提升可读性）
ACTION_LABELS = {
    ("chat", "send"): "发送消息",
    ("chat", "receive"): "接收消息",
    ("schedule", "create"): "创建日程",
    ("schedule", "view"): "查看日程",
    ("schedule", "update"): "更新日程",
    ("clipboard", "copy"): "复制内容",
    ("clipboard", "paste"): "粘贴内容",
    ("knowledge", "search"): "搜索知识库",
    ("knowledge", "create"): "创建知识",
    ("memory", "search"): "搜索记忆",
    ("memory", "create"): "创建记忆",
    ("skill", "execute"): "执行技能",
    ("translate", "translate"): "翻译文本",
    ("snippet", "create"): "保存代码片段",
    ("snippet", "search"): "搜索代码片段",
}


def _label(module: str, action: str) -> str:
    """获取动作的中文标签"""
    return ACTION_LABELS.get((module, action), f"{module}:{action}")


# ── Phase 1: SQL 聚合 ────────────────────────────────────

async def _extract_frequent_actions(db: AsyncSession, days: int = ANALYSIS_DAYS) -> List[Dict]:
    """提取高频动作（按 module + action 聚合）"""
    cutoff = datetime.now() - timedelta(days=days)
    stmt = (
        select(
            ActionLog.module,
            ActionLog.action,
            func.count().label("count"),
        )
        .where(ActionLog.is_deleted == 0)
        .where(ActionLog.created_at >= cutoff)
        .group_by(ActionLog.module, ActionLog.action)
        .having(func.count() >= MIN_ACTION_COUNT)
        .order_by(func.count().desc())
        .limit(50)
    )
    result = await db.execute(stmt)
    return [
        {"module": row.module, "action": row.action, "count": row.count}
        for row in result.all()
    ]


async def _extract_time_patterns(db: AsyncSession, days: int = ANALYSIS_DAYS) -> List[Dict]:
    """提取时间规律（按小时分布）"""
    cutoff = datetime.now() - timedelta(days=days)
    stmt = (
        select(
            ActionLog.module,
            ActionLog.action,
            func.hour(ActionLog.created_at).label("hour"),
            func.count().label("count"),
        )
        .where(ActionLog.is_deleted == 0)
        .where(ActionLog.created_at >= cutoff)
        .group_by(ActionLog.module, ActionLog.action, func.hour(ActionLog.created_at))
        .having(func.count() >= 2)
        .order_by(func.count().desc())
        .limit(100)
    )
    result = await db.execute(stmt)
    return [
        {"module": row.module, "action": row.action, "hour": row.hour, "count": row.count}
        for row in result.all()
    ]


async def _extract_action_sequences(db: AsyncSession, days: int = ANALYSIS_DAYS) -> List[Dict]:
    """提取动作序列（按 session_id 分组，找连续动作）

    如果 session_id 数据不足，降级为按时间窗口分组
    """
    cutoff = datetime.now() - timedelta(days=days)

    # 优先用 session_id
    stmt = (
        select(
            ActionLog.session_id,
            ActionLog.module,
            ActionLog.action,
            ActionLog.created_at,
        )
        .where(ActionLog.is_deleted == 0)
        .where(ActionLog.created_at >= cutoff)
        .where(ActionLog.session_id != "")
        .order_by(ActionLog.session_id, ActionLog.created_at)
        .limit(5000)
    )
    result = await db.execute(stmt)
    rows = result.all()

    # 按 session_id 分组
    sessions: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
    for row in rows:
        sessions[row.session_id].append((row.module, row.action))

    # 如果 session_id 数据不足，降级为按 30 分钟窗口分组
    if len(sessions) < 10:
        stmt = (
            select(
                ActionLog.module,
                ActionLog.action,
                ActionLog.created_at,
            )
            .where(ActionLog.is_deleted == 0)
            .where(ActionLog.created_at >= cutoff)
            .order_by(ActionLog.created_at)
            .limit(5000)
        )
        result = await db.execute(stmt)
        rows = result.all()

        # 按 30 分钟窗口分组
        sessions = defaultdict(list)
        window_start = None
        window_id = 0
        for row in rows:
            if window_start is None or (row.created_at - window_start).total_seconds() > 1800:
                window_start = row.created_at
                window_id += 1
            sessions[f"window-{window_id}"].append((row.module, row.action))

    # 提取长度为 2-4 的子序列
    sequence_counter: Counter = Counter()
    for session_id, actions in sessions.items():
        if len(actions) < 2:
            continue
        # 去重连续重复动作
        deduped = [actions[0]]
        for a in actions[1:]:
            if a != deduped[-1]:
                deduped.append(a)
        # 提取子序列
        for length in range(2, min(5, len(deduped) + 1)):
            for i in range(len(deduped) - length + 1):
                seq = tuple(deduped[i:i + length])
                sequence_counter[seq] += 1

    # 过滤低频序列
    return [
        {"sequence": list(seq), "count": count}
        for seq, count in sequence_counter.most_common(20)
        if count >= MIN_SEQUENCE_COUNT
    ]


# ── Phase 2: 启发式规则 ──────────────────────────────────

def _identify_patterns(
    frequent_actions: List[Dict],
    time_patterns: List[Dict],
    sequences: List[Dict],
) -> List[Dict]:
    """启发式规则识别行为模式"""
    patterns = []
    seen_keys = set()  # 用 (module, action) 去重

    # 规则 1: 高频单动作 → 「习惯性操作」
    for action in frequent_actions[:15]:
        key = (action["module"], action["action"])
        if key in seen_keys:
            continue
        label = _label(action["module"], action["action"])
        patterns.append({
            "description": f"频繁{label}（{action['count']}次）",
            "frequency": action["count"],
            "actions": [label],
            "module": action["module"],
            "action": action["action"],
            "type": "frequent_action",
        })
        seen_keys.add(key)

    # 规则 2: 高频序列 → 「操作流程」
    for seq in sequences[:10]:
        if seq["count"] < MIN_SEQUENCE_COUNT:
            continue
        labels = [_label(m, a) for m, a in seq["sequence"]]
        seq_key = tuple((m, a) for m, a in seq["sequence"])
        if seq_key in seen_keys:
            continue
        desc = " → ".join(labels)
        patterns.append({
            "description": f"习惯性流程：{desc}",
            "frequency": seq["count"],
            "actions": labels,
            "type": "sequence",
        })
        seen_keys.add(seq_key)

    # 规则 3: 时间规律 → 「定时习惯」
    time_groups: Dict[Tuple[str, str], List[Dict]] = defaultdict(list)
    for tp in time_patterns:
        key = (tp["module"], tp["action"])
        time_groups[key].append(tp)

    for (module, action), hours in time_groups.items():
        key = (module, action)
        if key in seen_keys:
            continue
        if len(hours) < 2:
            continue
        total = sum(h["count"] for h in hours)
        if total < MIN_ACTION_COUNT:
            continue

        peak_hours = sorted(hours, key=lambda x: x["count"], reverse=True)[:2]
        peak_labels = []
        for h in peak_hours:
            if 6 <= h["hour"] < 12:
                peak_labels.append("早上")
            elif 12 <= h["hour"] < 18:
                peak_labels.append("下午")
            elif 18 <= h["hour"] < 22:
                peak_labels.append("晚上")
            else:
                peak_labels.append("深夜")

        if len(set(peak_labels)) <= 2:
            label = _label(module, action)
            time_str = "、".join(set(peak_labels))
            patterns.append({
                "description": f"习惯在{time_str}{label}",
                "frequency": total,
                "actions": [label],
                "module": module,
                "action": action,
                "type": "time_pattern",
            })
            seen_keys.add(key)

    patterns.sort(key=lambda x: x["frequency"], reverse=True)
    return patterns[:MAX_PATTERNS]


# ── Phase 3: LLM 分析（ProactiveAgent 借鉴）──────────────

SUGGESTION_PROMPT = """你是一个行为分析专家，负责从用户行为数据中提炼有价值的技能建议。

## 系统背景
这是一个 AI 助手系统，用户可以通过「技能」来自动化重复操作。
技能 = 一组预定义的指令，当用户触发时自动执行。
例如：「早间助手」技能 = 查询今日日程 + 生成待办清单 + 设置提醒。

## 用户行为数据
{pattern_summary}

## 任务
分析用户行为数据，判断是否存在可以自动化的用户习惯。

**必须严格遵守以下流程：**

Step 1 - Purpose（分析用户目的）：
- 这些行为数据反映了用户什么样的使用目的？
- 用户在解决什么问题？

Step 2 - Thoughts（思考是否有价值）：
- 这些行为是否有自动化价值？
- 单个高频操作通常没有自动化价值（如"频繁发送消息"）
- 多个动作组成的流程才有自动化价值（如"查日程→创建待办→设提醒"）

Step 3 - Decision（决策）：
- 如果有有价值的技能建议，输出 JSON 数组
- 如果没有，直接输出空数组 []

## 判断原则（严格遵守）
1. **只建议真正有价值的技能** — 如果行为数据没有明显的自动化价值，返回 []
2. **不要硬凑** — 频率低于 5 次的操作不值得做成技能
3. **避免过于简单的技能** — 单个高频操作不值得做成技能
4. **优先建议流程型技能** — 多个动作组成的序列更有自动化价值
5. **不建议已解决的模式** — 如果某个行为模式已被技能覆盖，跳过

## 好建议 vs 坏建议

✅ 好建议：
- 用户每天早上先查日程再创建待办 → 「早间规划助手」
- 用户收到外文消息后总是去翻译 → 「智能翻译助手」
- 用户复制代码后总是格式化保存 → 「代码整理助手」

❌ 坏建议：
- 用户频繁发送消息 → （太简单，不值得自动化）
- 用户经常查看日程 → （单个操作，没有流程价值）
- 用户搜索知识库 → （这是正常功能使用，不是习惯）

## 输出格式（严格 JSON）
```json
{{
  "purpose": "用户行为目的分析",
  "thoughts": "是否有自动化价值的思考过程",
  "suggestions": [
    {{
      "name": "技能名称（4字以内，简洁有力）",
      "description": "一句话说清楚这个技能做什么、帮用户省什么时间",
      "trigger_hint": "什么时候应该触发这个技能"
    }}
  ]
}}
```

如果没有有价值的建议，suggestions 为空数组：`"suggestions": []`
只输出 JSON，不要任何其他文字。"""


async def _generate_suggestions_with_llm(
    patterns: List[Dict],
    llm=None,
) -> Dict:
    """用 LLM 从行为模式生成技能建议（ProactiveAgent 借鉴）

    返回：{"purpose": str, "thoughts": str, "suggestions": list}
    """
    if not llm or not patterns:
        return {"purpose": "", "thoughts": "", "suggestions": []}

    # 构建模式摘要（只包含未解决的）
    pattern_summary = "\n".join(
        f"- {p['description']}（{p['type']}，频率: {p['frequency']}次）"
        for p in patterns[:10]
    )

    prompt = SUGGESTION_PROMPT.format(pattern_summary=pattern_summary)

    try:
        from langchain_core.messages import HumanMessage
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        content = response.content if hasattr(response, "content") else str(response)

        # 解析 JSON
        import json
        import re
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            result = json.loads(json_match.group())
            if isinstance(result, dict):
                purpose = result.get("purpose", "")
                thoughts = result.get("thoughts", "")
                suggestions = result.get("suggestions", [])

                # 过滤无效建议
                valid = []
                for s in suggestions:
                    if isinstance(s, dict) and s.get("name") and s.get("description"):
                        valid.append({
                            "name": s["name"][:50],
                            "description": s["description"][:200],
                            "trigger_hint": s.get("trigger_hint", ""),
                        })

                logger.info(f"[behavior_analyzer] LLM 分析: purpose={purpose[:50]}, thoughts={thoughts[:50]}, suggestions={len(valid)}")
                return {
                    "purpose": purpose,
                    "thoughts": thoughts,
                    "suggestions": valid[:MAX_SUGGESTIONS],
                }
    except Exception as e:
        logger.warning(f"[behavior_analyzer] LLM 建议生成失败（降级跳过）: {e}")

    return {"purpose": "", "thoughts": "", "suggestions": []}


# ── 主分析流程 ────────────────────────────────────────────

class BehaviorAnalyzer:
    """行为分析引擎"""

    def __init__(self):
        self.pattern_repo = BehaviorPatternRepository()
        self.suggestion_repo = SkillSuggestionRepository()

    async def analyze(
        self,
        db: AsyncSession,
        user_id: int = 0,
        llm=None,
    ) -> Dict:
        """执行完整分析流程

        ProactiveAgent 借鉴：
          - 只分析未解决的模式
          - 只生成未被忽略的建议
          - 返回 LLM 分析过程（purpose/thoughts）
        """
        logger.info(f"[behavior_analyzer] 开始分析 user_id={user_id}")

        # Phase 1: SQL 聚合
        frequent_actions = await _extract_frequent_actions(db)
        time_patterns = await _extract_time_patterns(db)
        sequences = await _extract_action_sequences(db)

        logger.info(
            f"[behavior_analyzer] Phase 1 完成: "
            f"高频动作={len(frequent_actions)}, "
            f"时间规律={len(time_patterns)}, "
            f"序列={len(sequences)}"
        )

        # Phase 2: 启发式规则识别模式
        identified = _identify_patterns(frequent_actions, time_patterns, sequences)
        logger.info(f"[behavior_analyzer] Phase 2 完成: 识别 {len(identified)} 个模式")

        # 过滤已解决的模式（ProactiveAgent 借鉴）
        existing_patterns = await self.pattern_repo.find_all(db, user_id=user_id)
        solved_descriptions = {p.description for p in existing_patterns if p.is_solved == 1}
        unsolved = [p for p in identified if p["description"] not in solved_descriptions]

        if len(unsolved) < len(identified):
            logger.info(f"[behavior_analyzer] 跳过 {len(identified) - len(unsolved)} 个已解决模式")

        # 写入 behavior_pattern 表（去重：按 description 判断）
        new_patterns = []
        for p in unsolved:
            existing = await self._find_pattern_by_description(db, p["description"], user_id)
            if existing:
                if p["frequency"] > existing.frequency:
                    await self.pattern_repo.mapper.update(db, existing.id, {
                        "frequency": p["frequency"],
                        "actions": p["actions"],
                    })
            else:
                created = await self.pattern_repo.create(db, {
                    "description": p["description"],
                    "frequency": p["frequency"],
                    "actions": p["actions"],
                    "user_id": user_id,
                })
                new_patterns.append(created)

        logger.info(f"[behavior_analyzer] 写入模式: {len(new_patterns)} 个新增, {len(unsolved) - len(new_patterns)} 个更新")

        # 断点修复：高频模式自动创建意图
        auto_intents = []
        for p in new_patterns:
            if p.frequency >= AUTO_INTENT_FREQUENCY and p.actions:
                try:
                    from app.services.intent_learning_service import intent_learning_service
                    result = await intent_learning_service.create_intent_from_pattern(db, p.id)
                    if result:
                        auto_intents.append(result)
                        logger.info(f"[behavior_analyzer] 模式→意图: {result}")
                except Exception as e:
                    logger.debug(f"[behavior_analyzer] 模式→意图跳过: {e}")
        if auto_intents:
            logger.info(f"[behavior_analyzer] 自动创建 {len(auto_intents)} 个意图")

        # Phase 3: LLM 分析（ProactiveAgent 借鉴：结构化输出）
        llm_result = {"purpose": "", "thoughts": "", "suggestions": []}
        new_suggestions = []

        if new_patterns and llm:
            # 获取已被忽略 3 次以上的建议名称（不再重复建议）
            ignored_suggestions = await self.suggestion_repo.find_all(
                db, user_id=user_id, status=2,
            )
            ignored_names = {s.name for s in ignored_suggestions if s.ignore_count >= IGNORE_THRESHOLD}

            llm_result = await _generate_suggestions_with_llm(unsolved, llm)

            for s in llm_result["suggestions"]:
                # 跳过已被忽略的建议
                if s["name"] in ignored_names:
                    logger.info(f"[behavior_analyzer] 跳过已忽略建议: {s['name']}")
                    continue

                existing_sug = await self._find_suggestion_by_name(db, s["name"], user_id)
                if not existing_sug:
                    created = await self.suggestion_repo.create(db, {
                        "pattern_id": new_patterns[0].id if new_patterns else 0,
                        "name": s["name"],
                        "description": s.get("description", ""),
                        "status": 0,
                        "user_id": user_id,
                    })
                    new_suggestions.append(created)
            logger.info(f"[behavior_analyzer] Phase 3 完成: {len(new_suggestions)} 个新建议")
        elif not llm:
            logger.info("[behavior_analyzer] Phase 3 跳过: 无 LLM，降级为纯规则分析")

        return {
            "patterns_found": len(unsolved),
            "patterns_new": len(new_patterns),
            "suggestions_new": len(new_suggestions),
            "auto_intents": len(auto_intents),
            "patterns": [self._pattern_to_dict(p) for p in unsolved],
            "suggestions": [self._suggestion_to_dict(s) for s in new_suggestions],
            "purpose": llm_result.get("purpose", ""),
            "thoughts": llm_result.get("thoughts", ""),
        }

    async def _find_pattern_by_description(
        self, db: AsyncSession, description: str, user_id: int,
    ) -> Optional[BehaviorPattern]:
        stmt = select(BehaviorPattern).where(
            BehaviorPattern.description == description,
            BehaviorPattern.user_id == user_id,
            BehaviorPattern.is_deleted == 0,
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def _find_suggestion_by_name(
        self, db: AsyncSession, name: str, user_id: int,
    ) -> Optional[SkillSuggestion]:
        stmt = select(SkillSuggestion).where(
            SkillSuggestion.name == name,
            SkillSuggestion.user_id == user_id,
            SkillSuggestion.is_deleted == 0,
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    def _pattern_to_dict(p: Dict) -> Dict:
        return {
            "description": p["description"],
            "frequency": p["frequency"],
            "actions": p["actions"],
            "type": p.get("type", "unknown"),
        }

    @staticmethod
    def _suggestion_to_dict(s) -> Dict:
        return {
            "id": s.id,
            "name": s.name,
            "description": s.description,
        }


# ── 全局单例 ──────────────────────────────────────────────

behavior_analyzer = BehaviorAnalyzer()
