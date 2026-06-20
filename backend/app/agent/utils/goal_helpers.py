"""Goal 模式辅助函数 — 循环检测、DAG 排序、Guardrail 校验"""
import re
from typing import Optional

from langchain_core.messages import HumanMessage

from app.core.logging import get_logger

logger = get_logger(__name__)


# ── 循环检测器 ─────────────────────────────────────────────

class LoopDetector:
    """检测同一子任务连续失败，防止死循环"""
    def __init__(self, max_consecutive: int = 3):
        self._history: list[tuple[int, str]] = []
        self._max = max_consecutive

    def record(self, subtask_id: int, status: str):
        self._history.append((subtask_id, status))
        if len(self._history) > self._max * 2:
            self._history = self._history[-self._max * 2:]

    def is_looping(self) -> tuple:
        if len(self._history) < self._max:
            return False, ""
        recent = self._history[-self._max:]
        ids = [r[0] for r in recent]
        statuses = [r[1] for r in recent]
        if len(set(ids)) == 1 and all(s == "failed" for s in statuses):
            return True, f"子任务 #{ids[0]} 连续失败 {self._max} 次"
        return False, ""

    def get_stuck_task_id(self):
        if len(self._history) < self._max:
            return None
        recent = self._history[-self._max:]
        ids = [r[0] for r in recent]
        statuses = [r[1] for r in recent]
        if len(set(ids)) == 1 and all(s == "failed" for s in statuses):
            return ids[0]
        return None

    def reset(self):
        self._history.clear()


# P1 fix: 按 thread_id 隔离（LangGraph 官方推荐），避免并发请求间状态泄漏
_loop_detectors: dict[str, LoopDetector] = {}


def _get_loop_detector(thread_id: str) -> LoopDetector:
    """获取按 thread_id 隔离的 LoopDetector 实例"""
    if thread_id not in _loop_detectors:
        _loop_detectors[thread_id] = LoopDetector()
    # 清理过多的实例（保留最近 100 个）
    if len(_loop_detectors) > 100:
        oldest_keys = sorted(_loop_detectors.keys())[:50]
        for k in oldest_keys:
            del _loop_detectors[k]
    return _loop_detectors[thread_id]


# P2 fix: 按 LLM 实例 ID 缓存，避免跨模型共享
_semantic_llm_caches: dict[int, Any] = {}  # {id(llm): structured_llm}


def _get_semantic_llm(llm):
    """获取按 LLM 实例隔离的语义校验模型"""
    key = id(llm)
    if key not in _semantic_llm_caches:
        from app.agent.structured_schemas import SemanticSubtaskValidation
        _semantic_llm_caches[key] = llm.with_structured_output(SemanticSubtaskValidation)
    # 清理过多的缓存
    if len(_semantic_llm_caches) > 20:
        oldest_keys = sorted(_semantic_llm_caches.keys())[:10]
        for k in oldest_keys:
            del _semantic_llm_caches[k]
    return _semantic_llm_caches[key]


# ── 输入校验 ───────────────────────────────────────────────

def _validate_goal_definition(goal_definition: str) -> tuple:
    """Goal 定义前置校验"""
    if not goal_definition or not goal_definition.strip():
        return False, "目标定义不能为空"
    cleaned = goal_definition.strip()
    if len(cleaned) < 10:
        return False, f"目标定义过短（{len(cleaned)} 字符），至少需要 10 个字符"
    if len(cleaned) > 2000:
        return False, f"目标定义过长（{len(cleaned)} 字符），请精简到 2000 字符以内"
    meaningful = re.sub(r'[?!？！.。，,\s]+', '', cleaned)
    if len(meaningful) < 5:
        return False, "目标定义缺少实质内容，请描述具体要做什么"
    return True, ""


# ── 依赖关系校验（P3+P4 fix）─────────────────────────────

def _validate_dependencies(goal_subtasks: list) -> list[str]:
    """校验子任务依赖关系，返回问题列表

    检查：
      1. 重复 ID
      2. 依赖不存在的 ID
      3. 循环依赖（拓扑排序）
    """
    issues = []

    # 1. 重复 ID
    ids = [t["id"] for t in goal_subtasks]
    seen = set()
    for tid in ids:
        if tid in seen:
            issues.append(f"子任务 ID 重复: {tid}")
        seen.add(tid)

    # 2. 依赖不存在的 ID
    id_set = set(ids)
    for t in goal_subtasks:
        for dep in t.get("dependencies", []):
            if dep not in id_set:
                issues.append(f"任务{t['id']}依赖不存在的任务{dep}")

    # 3. 循环依赖（拓扑排序）
    visited = set()
    in_stack = set()
    dep_map = {t["id"]: t.get("dependencies", []) for t in goal_subtasks}

    def _has_cycle(task_id: int) -> bool:
        if task_id in in_stack:
            return True
        if task_id in visited:
            return False
        visited.add(task_id)
        in_stack.add(task_id)
        for dep in dep_map.get(task_id, []):
            if dep in dep_map and _has_cycle(dep):
                return True
        in_stack.discard(task_id)
        return False

    for t in goal_subtasks:
        if _has_cycle(t["id"]):
            issues.append(f"检测到循环依赖（涉及任务{t['id']}）")
            break

    return issues


# ── 子任务辅助函数 ─────────────────────────────────────────

def _get_next_pending_subtask(goal_subtasks: list) -> "dict | None":
    """获取下一个待执行子任务（DAG 拓扑排序）"""
    if not goal_subtasks:
        return None
    done_ids = {t["id"] for t in goal_subtasks if t.get("status") == "done"}
    for task in goal_subtasks:
        if task.get("status") != "pending":
            continue
        deps = task.get("dependencies", [])
        if all(d in done_ids for d in deps):
            return task
    for task in goal_subtasks:
        if task.get("status") == "pending":
            return task
    return None


def _get_parallel_ready_tasks(goal_subtasks: list, max_parallel: int = 3) -> list:
    """获取可并行执行的 pending 子任务"""
    if not goal_subtasks:
        return []
    done_ids = {t["id"] for t in goal_subtasks if t.get("status") == "done"}
    ready = []
    for task in goal_subtasks:
        if task.get("status") != "pending":
            continue
        deps = task.get("dependencies", [])
        if all(d in done_ids for d in deps):
            ready.append(task)
        if len(ready) >= max_parallel:
            break
    return ready


def _update_subtask_status(goal_subtasks: list, task_id: int, status: str, progress: int = 0) -> list:
    """更新指定子任务状态"""
    return [
        {**t, "status": status, "progress": progress} if t.get("id") == task_id else t
        for t in goal_subtasks
    ]


def _build_goal_progress_text(goal_subtasks: list) -> str:
    """构建进度文本"""
    if not goal_subtasks:
        return ""
    done = [t for t in goal_subtasks if t.get("status") == "done"]
    failed = [t for t in goal_subtasks if t.get("status") == "failed"]
    in_progress = [t for t in goal_subtasks if t.get("status") == "in_progress"]
    pending = [t for t in goal_subtasks if t.get("status") == "pending"]
    lines = []
    if done:
        lines.append("### ✅ 已完成")
        for t in done:
            lines.append(f"  ✅ #{t['id']} {t['title']}")
    if failed:
        lines.append("### ❌ 失败")
        for t in failed:
            lines.append(f"  ❌ #{t['id']} {t['title']}")
    if in_progress:
        lines.append("### 🔄 执行中")
        for t in in_progress:
            lines.append(f"  🔄 #{t['id']} {t['title']}")
    if pending:
        lines.append("### ⏳ 待执行")
        for t in pending:
            deps = t.get('dependencies', [])
            dep_str = f" (依赖: {','.join(str(d) for d in deps)})" if deps else ""
            lines.append(f"  ⏳ #{t['id']} {t['title']}{dep_str}")
    return "\n".join(lines)


def _parse_goal_subtasks(text: str) -> list:
    """从 LLM 回复中解析 [目标拆解] 格式的子任务列表。

    格式示例：
        [目标拆解]
        • 搜索 Loop Engineering 公司信息 - [pending] (0%)
        • 分析技术路线 - [pending] (0%) -> 依赖: 1
    """
    tasks = []
    match = re.search(r'\[目标拆解\]\s*\n([\s\S]*?)(?=\n\n|═|$)', text)
    if not match:
        return tasks

    lines = match[1].split('\n')
    task_id = 0
    for line in lines:
        trimmed = line.strip()
        if not trimmed:
            continue
        task_match = re.match(
            r'^[•\-\d\.]+\s*(.+?)\s*-\s*\[(pending|in_progress|done|failed)\](?:\s*\((\d+)%\))?(?:\s*->\s*依赖:\s*([\d,\s]+))?',
            trimmed
        )
        if task_match:
            task_id += 1
            title = task_match[1].strip()
            status_str = task_match[2]
            progress = int(task_match[3]) if task_match[3] else 0
            deps_str = task_match[4]
            dependencies = [int(d.strip()) for d in deps_str.split(',') if d.strip().isdigit()] if deps_str else []
            tasks.append({
                "id": task_id,
                "title": title,
                "status": status_str,
                "progress": progress,
                "dependencies": dependencies,
            })
    return tasks


# ── Guardrail 校验 ─────────────────────────────────────────

async def _guardrail_check_subtask(answer_text: str, subtask_title: str, llm=None) -> tuple:
    """子任务输出 Guardrail 校验（格式 + 语义双层）

    Returns:
        (passed: bool, reason: str)
    """
    # ── 第一层：格式校验（零成本）──
    if not answer_text or len(answer_text.strip()) < 20:
        return False, "输出内容过短或为空"
    failure_markers = ["抱歉", "无法", "失败", "错误", "不可用", "unable", "error", "failed"]
    marker_count = sum(1 for m in failure_markers if m in answer_text)
    if marker_count >= 3 and len(answer_text) < 100:
        return False, f"输出包含多个失败标记 ({marker_count} 个)"
    promise_patterns = [r"^我来帮你", r"^让我", r"^我将要", r"^接下来我会", r"^我需要先", r"^首先我需要", r"^我先帮你", r"^我来为你"]
    for pattern in promise_patterns:
        if re.match(pattern, answer_text.strip()):
            return False, "输出为承诺性回复，缺少实质内容"

    # ── 第二层：语义校验（LLM，格式通过后执行）──
    if llm is not None:
        try:
            semantic_llm = _get_semantic_llm(llm)
            validation_prompt = f"""评估以下子任务输出的质量。

## 子任务
{subtask_title}

## 输出内容
{answer_text[:2000]}

## 评估标准
1. 是否实质完成了子任务（不是承诺性回复）
2. 与子任务目标的相关性（1-10）
3. 输出质量（1-10）
4. 是否包含幻觉/捏造内容"""
            result = await semantic_llm.ainvoke([HumanMessage(content=validation_prompt)])
            if not result.completed:
                return False, f"语义校验未完成子任务: {'; '.join(result.issues[:3])}"
            if result.has_hallucination:
                return False, "输出包含幻觉/捏造内容"
            if result.relevance < 5:
                return False, f"与子任务目标相关性过低 ({result.relevance}/10)"
            if result.quality_score < 4:
                return False, f"输出质量过低 ({result.quality_score}/10): {result.suggestion}"
        except Exception as e:
            logger.debug(f"[guardrail] 语义校验失败（降级为仅格式校验）: {e}")

    return True, ""
