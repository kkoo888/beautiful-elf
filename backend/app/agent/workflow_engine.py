"""工作流执行引擎 — DAG 拓扑排序 + 逐步执行

职责:
  - 解析 DAG 定义（nodes + edges）
  - 拓扑排序确定执行顺序
  - 逐步执行节点，记录状态
  - 错误处理 + 状态持久化

注意:
  - 本模块是 Agent 引擎的子系统，由 workflow_service 调用
  - 不含路由细节
"""
from typing import Dict, List, Any
from datetime import datetime

from app.core.logging import get_logger

logger = get_logger(__name__)


class WorkflowEngine:
    """工作流执行引擎"""

    def __init__(self):
        self._handlers: Dict[str, Any] = {}

    def register_handler(self, node_type: str, handler):
        """
        注册节点类型处理器。

        Args:
            node_type: 节点类型（如 "llm", "tool", "condition"）
            handler: async handler(node_def: dict, context: dict) -> dict
        """
        self._handlers[node_type] = handler

    async def execute(self, db, workflow_id: int, input_data: dict = None) -> dict:
        """
        执行工作流。

        Args:
            db: 数据库会话
            workflow_id: 工作流 ID
            input_data: 输入参数

        Returns:
            最终上下文 dict
        """
        from app.repository.workflow_repo import WorkflowRepository
        repo = WorkflowRepository()

        workflow = await repo.find_by_id(db, workflow_id)
        if not workflow:
            raise ValueError(f"工作流 {workflow_id} 不存在")

        dag = workflow.dag_json or {}
        nodes = dag.get("nodes", {})
        edges = dag.get("edges", [])

        # 创建运行记录
        run = await repo.create_run(db, {
            "workflow_id": workflow_id,
            "status": 1,  # 运行中
            "trigger_type": 0,
            "input_json": input_data,
            "started_at": datetime.utcnow(),
        })

        try:
            order = self._topological_sort(nodes, edges)
            context = input_data or {}

            for step_name in order:
                step_def = nodes.get(step_name, {})
                step_type = step_def.get("type", "default")

                # 创建步骤记录
                step_run = await repo.create_step_run(db, {
                    "run_id": run.id,
                    "step_name": step_name,
                    "step_type": step_type,
                    "status": 1,  # 运行中
                    "input_json": context,
                    "started_at": datetime.utcnow(),
                })

                try:
                    handler = self._handlers.get(step_type)
                    if not handler:
                        raise ValueError(f"未注册的节点类型: {step_type}")

                    result = await handler(step_def, context)
                    context[step_name] = result

                    # 更新步骤成功
                    await repo.update_step_run(db, step_run.id, {
                        "status": 2,  # 成功
                        "output_json": result,
                        "finished_at": datetime.utcnow(),
                    })

                except Exception as e:
                    # 更新步骤失败
                    await repo.update_step_run(db, step_run.id, {
                        "status": 3,  # 失败
                        "error_message": str(e),
                        "finished_at": datetime.utcnow(),
                    })
                    raise

            # 更新运行成功
            duration = int((datetime.utcnow() - run.started_at).total_seconds() * 1000) if run.started_at else 0
            await repo.update_run(db, run.id, {
                "status": 2,  # 成功
                "output_json": context,
                "finished_at": datetime.utcnow(),
                "duration_ms": duration,
            })
            return context

        except Exception as e:
            # 更新运行失败
            duration = int((datetime.utcnow() - run.started_at).total_seconds() * 1000) if run.started_at else 0
            await repo.update_run(db, run.id, {
                "status": 3,  # 失败
                "error_message": str(e),
                "finished_at": datetime.utcnow(),
                "duration_ms": duration,
            })
            raise

    def _topological_sort(self, nodes: dict, edges: list) -> List[str]:
        """
        DAG 拓扑排序。

        Args:
            nodes: {"node_name": {"type": "...", ...}}
            edges: [{"from": "a", "to": "b"}, ...]

        Returns:
            排序后的节点名称列表

        Raises:
            ValueError: 存在循环依赖
        """
        in_degree = {name: 0 for name in nodes}
        adjacency = {name: [] for name in nodes}

        for edge in edges:
            src, dst = edge.get("from", ""), edge.get("to", "")
            if src in adjacency and dst in in_degree:
                in_degree[dst] += 1
                adjacency[src].append(dst)

        queue = [n for n, d in in_degree.items() if d == 0]
        order = []

        while queue:
            node = queue.pop(0)
            order.append(node)
            for neighbor in adjacency.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(order) != len(nodes):
            raise ValueError("DAG 中存在循环依赖")

        return order


# ── 内置节点处理器 ────────────────────────────────────────

async def llm_handler(node_def: dict, context: dict) -> dict:
    """LLM 节点处理器"""
    prompt = node_def.get("prompt", "")
    # 替换上下文变量
    for key, value in context.items():
        prompt = prompt.replace(f"{{{key}}}", str(value))

    return {"prompt": prompt, "status": "completed"}


async def tool_handler(node_def: dict, context: dict) -> dict:
    """工具节点处理器"""
    tool_name = node_def.get("tool", "")
    tool_args = node_def.get("args", {})

    # 替换上下文变量
    for key, value in tool_args.items():
        if isinstance(value, str) and value.startswith("{") and value.endswith("}"):
            ctx_key = value[1:-1]
            if ctx_key in context:
                tool_args[key] = context[ctx_key]

    return {"tool": tool_name, "args": tool_args, "status": "completed"}


async def condition_handler(node_def: dict, context: dict) -> dict:
    """条件节点处理器"""
    condition = node_def.get("condition", "")
    # 简单条件评估
    try:
        result = eval(condition, {"context": context, "__builtins__": {}})
        return {"condition": condition, "result": bool(result)}
    except Exception as e:
        return {"condition": condition, "result": False, "error": str(e)}


def create_default_engine() -> WorkflowEngine:
    """创建带默认处理器的工作流引擎"""
    engine = WorkflowEngine()
    engine.register_handler("llm", llm_handler)
    engine.register_handler("tool", tool_handler)
    engine.register_handler("condition", condition_handler)
    return engine


# ── 全局单例 ──────────────────────────────────────────────

workflow_engine = create_default_engine()
