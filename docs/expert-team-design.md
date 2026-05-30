# 专家团工作流程设计

> 基于 `langgraph-for-agents` 技能的 Orchestrator-Worker 模式
> 设计日期：2026-05-30

---

## 一、整体架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           前端 (Electron)                               │
│                                                                         │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐  │
│  │  专家团管理面板    │  │  任务执行面板     │  │  实时进度面板         │  │
│  │                  │  │                  │  │                      │  │
│  │  · 新建专家团     │  │  · 选择专家团     │  │  · Timeline 进度条   │  │
│  │  · 添加角色       │  │  · 输入任务描述   │  │  · 角色执行状态      │  │
│  │  · 绑定技能       │  │  · 触发执行       │  │  · 技能调用详情      │  │
│  │  · 编辑/删除      │  │  · 查看历史       │  │  · 最终结果          │  │
│  └──────────────────┘  └────────┬─────────┘  └──────────▲───────────┘  │
│                                 │                       │              │
└─────────────────────────────────┼───────────────────────┼──────────────┘
                                  │ POST /api/v1/         │ WebSocket
                                  │ expert-teams/execute  │ expert_progress
                                  ▼                       │
┌─────────────────────────────────────────────────────────┼──────────────┐
│                        FastAPI 路由层                     │              │
│  /api/v1/expert-teams/*                                 │              │
│  /api/v1/expert-roles/*                                 │              │
│  /api/v1/expert-roles/{id}/skills/*                     │              │
└─────────────────────────────────┬───────────────────────┘              │
                                  │                                      │
                                  ▼                                      │
┌───────────────────────────────────────────────────────────────────────┐
│                        Celery 任务层                                   │
│  execute_expert_team(task_id, team_id, task_input)                    │
└─────────────────────────────┬─────────────────────────────────────────┘
                              │
                              ▼
┌───────────────────────────────────────────────────────────────────────┐
│                     LangGraph 工作流                                   │
│                                                                       │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐               │
│  │ orchestrator│───▶│ role_worker │───▶│ synthesizer │               │
│  │ (总指挥)     │    │ (角色执行)   │    │ (结果汇总)   │               │
│  └─────────────┘    └─────────────┘    └─────────────┘               │
│        │                  │                                           │
│        │           ┌──────┴──────┐                                    │
│        │           │ skill_call  │  ← 角色调用绑定的技能               │
│        │           │ (技能调用)   │                                    │
│        │           └─────────────┘                                    │
│        │                                                              │
│  实时 WebSocket 推送: role_start / skill_call / role_complete         │
└───────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌───────────────────────────────────────────────────────────────────────┐
│  MySQL: expert_teams / expert_roles / expert_role_skills              │
│         expert_team_runs / expert_role_runs                           │
│  Qdrant: knowledge_chunks (技能检索)                                   │
│  Redis: WebSocket 消息队列                                             │
└───────────────────────────────────────────────────────────────────────┘
```

---

## 二、数据库设计

### 1. expert_teams — 专家团

```sql
CREATE TABLE expert_teams (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(256)    NOT NULL COMMENT '专家团名称',
    description     VARCHAR(1024)   DEFAULT '' COMMENT '专家团描述',
    avatar          VARCHAR(512)    DEFAULT '' COMMENT '头像 URL',
    system_prompt   TEXT            DEFAULT NULL COMMENT '专家团系统提示词 (定义整体协作规则)',
    max_concurrent_roles TINYINT    NOT NULL DEFAULT 3 COMMENT '最大并发角色数 (防止资源争抢)',
    timeout_seconds INT UNSIGNED    NOT NULL DEFAULT 300 COMMENT '单次任务超时 (秒)',
    enabled         TINYINT         NOT NULL DEFAULT 1 COMMENT '是否启用',
    sort_order      INT             NOT NULL DEFAULT 0 COMMENT '排序权重',
    deleted         TINYINT         NOT NULL DEFAULT 0,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_expert_teams_enabled (deleted, enabled)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='专家团';
```

### 2. expert_roles — 专家团角色

```sql
CREATE TABLE expert_roles (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    team_id         BIGINT UNSIGNED NOT NULL COMMENT '所属专家团 ID',
    name            VARCHAR(128)    NOT NULL COMMENT '角色名称 (如: 研究员、编码者、审查员)',
    display_name    VARCHAR(256)    DEFAULT '' COMMENT '显示名称',
    description     VARCHAR(1024)   DEFAULT '' COMMENT '角色职责描述',
    avatar          VARCHAR(512)    DEFAULT '' COMMENT '角色头像/图标',
    role_type       VARCHAR(64)     NOT NULL DEFAULT 'worker' COMMENT '角色类型 (orchestrator/worker/reviewer)',
    system_prompt   TEXT            DEFAULT NULL COMMENT '角色系统提示词 (定义行为准则、输出格式)',
    llm_model       VARCHAR(128)    DEFAULT NULL COMMENT '使用的 LLM 模型 (为空则用默认)',
    temperature     DECIMAL(2,1)    DEFAULT NULL COMMENT '模型温度 (0.0-2.0)',
    max_tokens      INT UNSIGNED    DEFAULT NULL COMMENT '最大输出 token 数',
    execution_order TINYINT         NOT NULL DEFAULT 0 COMMENT '执行顺序 (0=并行, >0=串行)',
    depends_on      JSON            DEFAULT NULL COMMENT '依赖的角色 ID 列表',
    enabled         TINYINT         NOT NULL DEFAULT 1,
    sort_order      INT             NOT NULL DEFAULT 0,
    deleted         TINYINT         NOT NULL DEFAULT 0,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_expert_roles_team (team_id, deleted),
    INDEX idx_expert_roles_type (role_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='专家团角色';
```

### 3. expert_role_skills — 角色技能绑定

```sql
CREATE TABLE expert_role_skills (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    role_id         BIGINT UNSIGNED NOT NULL COMMENT '角色 ID',
    skill_id        BIGINT UNSIGNED NOT NULL COMMENT '技能 ID (关联 skills 表)',
    priority        TINYINT         NOT NULL DEFAULT 0 COMMENT '调用优先级 (数值越大越优先)',
    config_override JSON            DEFAULT NULL COMMENT '角色级别的技能配置覆盖',
    enabled         TINYINT         NOT NULL DEFAULT 1,
    deleted         TINYINT         NOT NULL DEFAULT 0,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_role_skill (role_id, skill_id),
    INDEX idx_role_skills_role (role_id),
    INDEX idx_role_skills_skill (skill_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='角色技能绑定';
```

### 4. expert_team_runs — 专家团运行记录

```sql
CREATE TABLE expert_team_runs (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    team_id         BIGINT UNSIGNED NOT NULL COMMENT '专家团 ID',
    status          TINYINT         NOT NULL DEFAULT 0 COMMENT '状态 (0=待运行, 1=运行中, 2=成功, 3=失败, 4=已取消)',
    task_input      TEXT            NOT NULL COMMENT '任务描述',
    output_json     JSON            DEFAULT NULL COMMENT '最终输出结果',
    error_message   VARCHAR(2048)   DEFAULT '' COMMENT '错误信息',
    started_at      DATETIME        DEFAULT NULL,
    finished_at     DATETIME        DEFAULT NULL,
    duration_ms     INT UNSIGNED    DEFAULT 0,
    deleted         TINYINT         NOT NULL DEFAULT 0,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_team_runs_team (team_id, status),
    INDEX idx_team_runs_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='专家团运行记录';
```

### 5. expert_role_runs — 角色执行记录

```sql
CREATE TABLE expert_role_runs (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    run_id          BIGINT UNSIGNED NOT NULL COMMENT '运行记录 ID',
    role_id         BIGINT UNSIGNED NOT NULL COMMENT '角色 ID',
    role_name       VARCHAR(128)    NOT NULL COMMENT '角色名称 (冗余，避免 JOIN)',
    status          TINYINT         NOT NULL DEFAULT 0 COMMENT '状态 (0=待运行, 1=运行中, 2=成功, 3=失败, 4=跳过)',
    input_json      JSON            DEFAULT NULL COMMENT '角色输入',
    output_json     JSON            DEFAULT NULL COMMENT '角色输出',
    skills_used     JSON            DEFAULT NULL COMMENT '实际调用的技能列表 [{skill_id, name, result}]',
    error_message   VARCHAR(2048)   DEFAULT '',
    started_at      DATETIME        DEFAULT NULL,
    finished_at     DATETIME        DEFAULT NULL,
    duration_ms     INT UNSIGNED    DEFAULT 0,
    deleted         TINYINT         NOT NULL DEFAULT 0,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_role_runs_run (run_id),
    INDEX idx_role_runs_role (role_id),
    INDEX idx_role_runs_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='角色执行记录';
```

### ER 关系图

```
expert_teams (1) ──────── (N) expert_roles
                                  │
                                  │ (N)
                                  ▼
                            expert_role_skills (N) ──── (1) skills

expert_team_runs (1) ──── (N) expert_role_runs
```

---

## 三、LangGraph 工作流设计

### 设计模式：Orchestrator-Worker（带技能调用）

```
┌──────────────┐
│    START     │
└──────┬───────┘
       │
┌──────▼───────┐
│  load_team   │  ← 从 MySQL 加载专家团 + 角色 + 技能配置
│  (加载配置)   │
└──────┬───────┘
       │
┌──────▼───────┐
│orchestrator  │  ← 总指挥分析任务，制定执行计划
│ (任务拆解)    │     输出: [{role_id, sub_task, priority}, ...]
└──────┬───────┘
       │
       │  assign_roles (Send 并行)
       ▼
┌──────────────────────────────────────────────────┐
│                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │ role_1   │  │ role_2   │  │ role_3   │  ...  │
│  │ (研究员)  │  │ (编码者)  │  │ (审查员)  │       │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘       │
│       │              │              │             │
│  ┌────▼─────┐  ┌────▼─────┐  ┌────▼─────┐       │
│  │skill_call│  │skill_call│  │skill_call│       │
│  │ (调技能)  │  │ (调技能)  │  │ (调技能)  │       │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘       │
│       │              │              │             │
│  实时 WebSocket 推送每个角色/技能的执行进度        │
└───────┼──────────────┼──────────────┼─────────────┘
        │              │              │
        └──────────────┼──────────────┘
                       │
                ┌──────▼───────┐
                │ synthesizer  │  ← 汇总所有角色输出
                │ (结果合并)    │
                └──────┬───────┘
                       │
                ┌──────▼───────┐
                │     END      │
                └──────────────┘
```

### State 定义

```python
from typing import TypedDict, Annotated
import operator

class ExpertTeamState(TypedDict):
    # === 任务输入 ===
    task_input: str                          # 用户输入的任务描述
    team_id: int                             # 专家团 ID
    run_id: int                              # 本次运行 ID

    # === 配置（load_team 填充）===
    team_config: dict                        # 专家团配置
    roles: list[dict]                        # 角色列表 [{id, name, type, prompt, skills: [...]}]

    # === 编排（orchestrator 填充）===
    execution_plan: list[dict]               # 执行计划 [{role_id, sub_task, priority, deps}]

    # === 执行结果（角色 Worker 累加）===
    role_results: Annotated[list[dict], operator.add]  # 各角色输出

    # === 最终输出 ===
    final_output: str                        # 汇总后的最终结果
    summary: str                             # 执行摘要

class RoleWorkerState(TypedDict):
    """单个角色的执行状态"""
    role: dict                               # 角色配置 {id, name, type, prompt, skills}
    sub_task: str                            # 该角色的子任务
    context: str                             # 前置角色的输出（依赖上下文）
    role_results: Annotated[list[dict], operator.add]  # 结果累加
```

### 核心节点

```python
# ============================================================
# 1. 加载专家团配置
# ============================================================
def load_team(state: ExpertTeamState) -> dict:
    """从 MySQL 加载专家团、角色、技能的完整配置"""
    team = db.query(ExpertTeam).get(state["team_id"])
    roles = db.query(ExpertRole).filter(
        ExpertRole.team_id == team.id,
        ExpertRole.deleted == 0,
        ExpertRole.enabled == 1,
    ).order_by(ExpertRole.execution_order).all()

    role_configs = []
    for role in roles:
        # 加载该角色绑定的技能
        skills = db.query(ExpertRoleSkill, Skill).join(
            Skill, ExpertRoleSkill.skill_id == Skill.id
        ).filter(
            ExpertRoleSkill.role_id == role.id,
            ExpertRoleSkill.deleted == 0,
            ExpertRoleSkill.enabled == 1,
        ).order_by(ExpertRoleSkill.priority.desc()).all()

        role_configs.append({
            "id": role.id,
            "name": role.name,
            "display_name": role.display_name,
            "type": role.role_type,
            "system_prompt": role.system_prompt,
            "llm_model": role.llm_model,
            "temperature": float(role.temperature) if role.temperature else 0.7,
            "max_tokens": role.max_tokens or 4096,
            "execution_order": role.execution_order,
            "depends_on": role.depends_on or [],
            "skills": [
                {
                    "id": s.Skill.id,
                    "name": s.Skill.name,
                    "display_name": s.Skill.display_name,
                    "description": s.Skill.description,
                    "config_override": s.ExpertRoleSkill.config_override,
                }
                for s in skills
            ],
        })

    return {
        "team_config": {
            "id": team.id,
            "name": team.name,
            "system_prompt": team.system_prompt,
            "max_concurrent_roles": team.max_concurrent_roles,
            "timeout_seconds": team.timeout_seconds,
        },
        "roles": role_configs,
    }


# ============================================================
# 2. 总指挥 — 任务拆解与角色分配
# ============================================================
def orchestrator(state: ExpertTeamState) -> dict:
    """总指挥分析任务，为每个角色分配子任务"""
    roles_desc = "\n".join([
        f"- {r['name']} ({r['type']}): {r['description']}\n"
        f"  可用技能: {', '.join(s['display_name'] for s in r['skills']) or '无'}\n"
        f"  依赖: {r['depends_on'] or '无'}"
        for r in state["roles"]
    ])

    system_prompt = state["team_config"].get("system_prompt", "")
    prompt = f"""{system_prompt}

你是一个任务编排专家。根据以下任务和可用角色，制定执行计划。

## 任务描述
{state['task_input']}

## 可用角色
{roles_desc}

## 要求
1. 为每个角色分配明确的子任务
2. 考虑角色间的依赖关系（execution_order 和 depends_on）
3. 可并行的角色尽量并行（execution_order = 0）
4. 每个子任务要具体、可执行

返回 JSON：
{{
    "execution_plan": [
        {{
            "role_id": 1,
            "role_name": "研究员",
            "sub_task": "具体任务描述",
            "priority": 1,
            "dependencies": []
        }}
    ],
    "reasoning": "执行计划的思考过程"
}}"""

    llm = get_llm(state["team_config"].get("llm_model"))
    result = llm.invoke(prompt)
    plan = json.loads(result.content)

    # 记录到 expert_team_runs
    save_team_run(state["run_id"], status=1, plan=plan)  # 1=运行中

    # WebSocket 推送：编排完成
    ws_broadcast("expert_progress", {
        "run_id": state["run_id"],
        "phase": "orchestrator",
        "status": "completed",
        "plan": plan["execution_plan"],
        "reasoning": plan.get("reasoning", ""),
    })

    return {"execution_plan": plan["execution_plan"]}


# ============================================================
# 3. 角色执行器 — 单个角色执行子任务
# ============================================================
def role_worker(state: RoleWorkerState) -> dict:
    """单个角色执行其子任务，可调用绑定的技能"""
    role = state["role"]
    sub_task = state["sub_task"]
    context = state.get("context", "")

    # WebSocket 推送：角色开始执行
    ws_broadcast("expert_progress", {
        "run_id": state.get("run_id"),
        "phase": "role_start",
        "role_id": role["id"],
        "role_name": role["name"],
        "sub_task": sub_task,
    })

    # 记录角色执行开始
    role_run_id = save_role_run(
        run_id=state["run_id"],
        role_id=role["id"],
        role_name=role["name"],
        status=1,  # 运行中
        input_json={"sub_task": sub_task, "context": context},
    )

    skills_used = []
    skill_results = []

    # ---- 第一步：角色决定是否需要调用技能 ----
    if role["skills"]:
        skill_decision = decide_skills(role, sub_task, context)

        # ---- 第二步：按需调用技能 ----
        for skill_call in skill_decision.get("skills_to_call", []):
            skill_info = next(
                (s for s in role["skills"] if s["name"] == skill_call["skill_name"]),
                None
            )
            if not skill_info:
                continue

            # WebSocket 推送：技能调用
            ws_broadcast("expert_progress", {
                "run_id": state.get("run_id"),
                "phase": "skill_call",
                "role_id": role["id"],
                "role_name": role["name"],
                "skill_name": skill_info["display_name"],
                "params": skill_call.get("params", {}),
            })

            try:
                skill_result = execute_skill(
                    skill_name=skill_info["name"],
                    params=skill_call.get("params", {}),
                    context=context,
                )
                skills_used.append({
                    "skill_id": skill_info["id"],
                    "name": skill_info["name"],
                    "display_name": skill_info["display_name"],
                    "status": "success",
                    "result": skill_result[:500],  # 截断保存
                })
                skill_results.append(
                    f"[技能 {skill_info['display_name']}]: {skill_result}"
                )
            except Exception as e:
                skills_used.append({
                    "skill_id": skill_info["id"],
                    "name": skill_info["name"],
                    "display_name": skill_info["display_name"],
                    "status": "failed",
                    "error": str(e)[:200],
                })

    # ---- 第三步：角色基于技能结果生成最终输出 ----
    skill_context = "\n\n".join(skill_results) if skill_results else ""
    full_context = f"{context}\n\n## 技能调用结果\n{skill_context}" if skill_context else context

    role_prompt = role.get("system_prompt", f"你是{role['name']}，请完成以下任务。")
    prompt = f"""{role_prompt}

## 你的任务
{sub_task}

## 前置上下文
{full_context}

## 要求
1. 基于任务和上下文，给出你专业的输出
2. 如果调用了技能，结合技能结果综合分析
3. 输出要结构化、清晰"""

    llm = get_llm(role.get("llm_model"), role.get("temperature", 0.7))
    result = llm.invoke(prompt)
    role_output = result.content

    # 记录角色执行完成
    save_role_run(
        role_run_id=role_run_id,
        status=2,  # 成功
        output_json={"output": role_output, "skills_used": skills_used},
        skills_used=skills_used,
    )

    # WebSocket 推送：角色完成
    ws_broadcast("expert_progress", {
        "run_id": state.get("run_id"),
        "phase": "role_complete",
        "role_id": role["id"],
        "role_name": role["name"],
        "output": role_output[:300],  # 截断推送
        "skills_used": [s["display_name"] for s in skills_used],
        "duration_ms": get_role_duration(role_run_id),
    })

    return {"role_results": [{
        "role_id": role["id"],
        "role_name": role["name"],
        "role_type": role["type"],
        "sub_task": sub_task,
        "output": role_output,
        "skills_used": skills_used,
    }]}


# ============================================================
# 4. 技能决策器 — 角色决定调用哪些技能
# ============================================================
def decide_skills(role: dict, sub_task: str, context: str) -> dict:
    """让 LLM 决定需要调用哪些技能来完成子任务"""
    skills_desc = "\n".join([
        f"- {s['name']}: {s['description']}"
        for s in role["skills"]
    ])

    prompt = f"""你是{role['name']}，需要完成以下任务。

## 任务
{sub_task}

## 可用技能
{skills_desc}

## 要求
1. 判断是否需要调用技能
2. 如果需要，选择合适的技能并给出参数
3. 技能可以不调、调一个或多个

返回 JSON：
{{
    "reasoning": "决策思考",
    "skills_to_call": [
        {{
            "skill_name": "技能名称",
            "params": {{}},
            "reason": "调用原因"
        }}
    ]
}}

如果不需要调用技能，返回 {{"reasoning": "...", "skills_to_call": []}}"""

    llm = get_llm(role.get("llm_model"), temperature=0.3)  # 低温度，稳定决策
    result = llm.invoke(prompt)
    return json.loads(result.content)


# ============================================================
# 5. 结果汇总器
# ============================================================
def synthesizer(state: ExpertTeamState) -> dict:
    """汇总所有角色的输出，生成最终结果"""
    results_text = "\n\n".join([
        f"### {r['role_name']} ({r['role_type']})\n"
        f"**子任务**: {r['sub_task']}\n"
        f"**输出**: {r['output']}\n"
        f"**调用技能**: {', '.join(s['display_name'] for s in r['skills_used']) or '无'}"
        for r in state["role_results"]
    ])

    prompt = f"""你是一个结果汇总专家。以下是一个专家团各角色的执行结果，请汇总为最终答案。

## 原始任务
{state['task_input']}

## 各角色执行结果
{results_text}

## 要求
1. 综合所有角色的输出，给出完整、连贯的最终答案
2. 去除重复内容，整合互补信息
3. 如果有冲突，以专业度更高的角色为准
4. 生成执行摘要（哪些角色参与、调用了哪些技能、总耗时）

返回 JSON：
{{
    "final_output": "完整的最终答案",
    "summary": "执行摘要"
}}"""

    llm = get_llm(state["team_config"].get("llm_model"))
    result = llm.invoke(prompt)
    output = json.loads(result.content)

    # 更新运行记录
    save_team_run(
        run_id=state["run_id"],
        status=2,  # 成功
        output_json={"final_output": output["final_output"], "summary": output["summary"]},
    )

    # WebSocket 推送：任务完成
    ws_broadcast("expert_progress", {
        "run_id": state["run_id"],
        "phase": "completed",
        "final_output": output["final_output"],
        "summary": output["summary"],
    })

    return {"final_output": output["final_output"], "summary": output["summary"]}
```

### 路由逻辑

```python
def assign_roles(state: ExpertTeamState) -> list[Send]:
    """根据执行计划分配角色，支持并行和串行"""
    sends = []
    completed_roles = {r["role_id"] for r in state["role_results"]}

    for plan in state["execution_plan"]:
        role_id = plan["role_id"]
        if role_id in completed_roles:
            continue  # 已完成，跳过

        # 检查依赖是否已完成
        deps = plan.get("dependencies", [])
        if all(d in completed_roles for d in deps):
            # 收集依赖角色的输出作为上下文
            dep_context = "\n\n".join([
                f"[{r['role_name']}的输出]: {r['output']}"
                for r in state["role_results"]
                if r["role_id"] in deps
            ])

            role = next(r for r in state["roles"] if r["id"] == role_id)
            sends.append(Send("role_worker", {
                "role": role,
                "sub_task": plan["sub_task"],
                "context": dep_context,
            }))

    return sends if sends else [Send("synthesizer", {})]
```

### 图构建

```python
from langgraph.graph import StateGraph, START, END

workflow = StateGraph(ExpertTeamState)

workflow.add_node("load_team", load_team)
workflow.add_node("orchestrator", orchestrator)
workflow.add_node("role_worker", role_worker)
workflow.add_node("synthesizer", synthesizer)

workflow.add_edge(START, "load_team")
workflow.add_edge("load_team", "orchestrator")
workflow.add_conditional_edges("orchestrator", assign_roles, ["role_worker", "synthesizer"])
workflow.add_edge("role_worker", "synthesizer")
workflow.add_edge("synthesizer", END)

expert_team_graph = workflow.compile()
```

---

## 四、完整执行流程示例

### 场景：代码审查专家团

**专家团配置：**

| 角色 | 职责 | 绑定技能 | 执行顺序 |
|---|---|---|---|
| 🔍 **研究员** | 分析代码结构、识别技术栈 | `code-analysis`, `file-reader` | 1（先执行）|
| 🐛 **审查员** | 发现 Bug、安全漏洞 | `security-scan`, `lint-check` | 2（依赖研究员）|
| ✍️ **改写者** | 根据审查结果修改代码 | `code-edit`, `refactor` | 3（依赖审查员）|
| 📝 **文档员** | 生成审查报告 | `markdown-gen` | 4（依赖全部）|

**执行流程：**

```
用户输入: "审查这段代码并修复问题" + 代码片段
        │
        ▼
┌─ load_team ──────────────────────────────────────────────┐
│  加载: 代码审查专家团 (4个角色, 6个技能绑定)              │
└───────────────────────┬─────────────────────────────────┘
                        │
┌─ orchestrator ───────────────────────────────────────────┐
│  分析任务 → 制定计划:                                     │
│  1. 研究员: "分析代码结构和技术栈" (并行)                  │
│  2. 审查员: "发现 Bug 和安全问题" (依赖1)                 │
│  3. 改写者: "根据审查结果修复代码" (依赖2)                │
│  4. 文档员: "生成审查报告" (依赖1,2,3)                    │
│                                                          │
│  WebSocket: expert_progress.phase=orchestrator            │
└───────────────────────┬─────────────────────────────────┘
                        │ Send()
                        ▼
┌─ role_worker (研究员) ───────────────────────────────────┐
│  📡 WS: expert_progress.phase=role_start (研究员)         │
│                                                          │
│  1. decide_skills → 调用 [code-analysis, file-reader]    │
│  📡 WS: expert_progress.phase=skill_call (code-analysis) │
│  📡 WS: expert_progress.phase=skill_call (file-reader)   │
│                                                          │
│  2. 基于技能结果生成分析报告                              │
│  📡 WS: expert_progress.phase=role_complete (研究员)      │
└───────────────────────┬─────────────────────────────────┘
                        │ (上下文传递给下一个角色)
                        ▼
┌─ role_worker (审查员) ───────────────────────────────────┐
│  📡 WS: expert_progress.phase=role_start (审查员)         │
│                                                          │
│  1. decide_skills → 调用 [security-scan, lint-check]     │
│  📡 WS: expert_progress.phase=skill_call (security-scan) │
│  📡 WS: expert_progress.phase=skill_call (lint-check)    │
│                                                          │
│  2. 综合分析，输出审查结果                                │
│  📡 WS: expert_progress.phase=role_complete (审查员)      │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
                    ... (改写者 → 文档员) ...
                        │
                        ▼
┌─ synthesizer ────────────────────────────────────────────┐
│  汇总所有角色输出:                                        │
│  - 代码结构分析 (研究员)                                  │
│  - Bug/漏洞列表 (审查员)                                  │
│  - 修复后代码 (改写者)                                    │
│  - 审查报告 (文档员)                                      │
│                                                          │
│  📡 WS: expert_progress.phase=completed                   │
└──────────────────────────────────────────────────────────┘
```

---

## 五、API 设计

### 专家团管理

```
GET    /api/v1/expert-teams                    # 列表
POST   /api/v1/expert-teams                    # 新建
GET    /api/v1/expert-teams/{id}               # 详情（含角色+技能）
PUT    /api/v1/expert-teams/{id}               # 更新
DELETE /api/v1/expert-teams/{id}               # 删除（软删除）
```

### 角色管理

```
GET    /api/v1/expert-teams/{team_id}/roles    # 角色列表
POST   /api/v1/expert-teams/{team_id}/roles    # 新建角色
PUT    /api/v1/expert-roles/{id}               # 更新角色
DELETE /api/v1/expert-roles/{id}               # 删除角色
```

### 技能绑定

```
GET    /api/v1/expert-roles/{role_id}/skills           # 已绑定技能列表
POST   /api/v1/expert-roles/{role_id}/skills           # 绑定技能
DELETE /api/v1/expert-roles/{role_id}/skills/{skill_id} # 解绑技能
PUT    /api/v1/expert-roles/{role_id}/skills/{skill_id} # 更新配置覆盖
```

### 执行

```
POST   /api/v1/expert-teams/{id}/execute       # 触发执行
GET    /api/v1/expert-team-runs                 # 运行历史
GET    /api/v1/expert-team-runs/{id}            # 运行详情（含各角色执行记录）
POST   /api/v1/expert-team-runs/{id}/cancel     # 取消执行
```

### WebSocket

```
WS /api/v1/ws?token=<jwt>

事件类型: expert_progress
payload: {
    "run_id": 123,
    "phase": "orchestrator|role_start|skill_call|role_complete|completed",
    "role_id": 1,          // 角色相关事件
    "role_name": "研究员",
    "skill_name": "...",   // 技能调用事件
    "output": "...",       // 完成事件
    "plan": [...],         // 编排事件
    "final_output": "...", // 最终结果
}
```

---

## 六、Pydantic 模型

```python
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

# === 请求模型 ===
class ExpertTeamCreate(BaseModel):
    name: str = Field(..., max_length=256)
    description: str = Field("", max_length=1024)
    system_prompt: Optional[str] = None
    max_concurrent_roles: int = Field(3, ge=1, le=10)
    timeout_seconds: int = Field(300, ge=30, le=3600)

class ExpertRoleCreate(BaseModel):
    name: str = Field(..., max_length=128)
    display_name: str = Field("", max_length=256)
    description: str = Field("", max_length=1024)
    role_type: str = Field("worker", pattern="^(orchestrator|worker|reviewer)$")
    system_prompt: Optional[str] = None
    llm_model: Optional[str] = None
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    execution_order: int = Field(0, ge=0)
    depends_on: Optional[list[int]] = None

class RoleSkillBind(BaseModel):
    skill_id: int
    priority: int = Field(0, ge=0)
    config_override: Optional[dict] = None

class ExpertTeamExecute(BaseModel):
    task_input: str = Field(..., min_length=1, max_length=10000)

# === 响应模型 ===
class ExpertTeamResponse(BaseModel):
    id: int
    name: str
    description: str
    roles_count: int
    enabled: bool
    created_at: datetime

class ExpertTeamDetailResponse(BaseModel):
    id: int
    name: str
    description: str
    system_prompt: Optional[str]
    max_concurrent_roles: int
    timeout_seconds: int
    roles: list["ExpertRoleResponse"]
    enabled: bool

class ExpertRoleResponse(BaseModel):
    id: int
    name: str
    display_name: str
    description: str
    role_type: str
    execution_order: int
    depends_on: Optional[list[int]]
    skills: list["RoleSkillResponse"]
    enabled: bool

class RoleSkillResponse(BaseModel):
    skill_id: int
    skill_name: str
    skill_display_name: str
    priority: int
    config_override: Optional[dict]

class ExpertTeamRunResponse(BaseModel):
    id: int
    team_id: int
    team_name: str
    status: int
    task_input: str
    output_json: Optional[dict]
    role_runs: list["ExpertRoleRunResponse"]
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    duration_ms: int

class ExpertRoleRunResponse(BaseModel):
    id: int
    role_id: int
    role_name: str
    status: int
    output_json: Optional[dict]
    skills_used: Optional[list[dict]]
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    duration_ms: int
```

---

## 七、前端管理界面设计

### 专家团管理面板

```
┌─────────────────────────────────────────────────────────────────┐
│  专家团管理                                        [+ 新建专家团] │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  🔬 代码审查专家团                           4个角色 6技能 │   │
│  │  专业的代码审查与修复团队                                  │   │
│  │  ┌───────────────────────────────────────────────────┐   │   │
│  │  │ 🔍 研究员 → 🐛 审查员 → ✍️ 改写者 → 📝 文档员     │   │   │
│  │  └───────────────────────────────────────────────────┘   │   │
│  │                              [编辑] [执行] [删除]         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  📊 数据分析专家团                           3个角色 4技能 │   │
│  │  ...                                                    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 专家团详情面板

```
┌─────────────────────────────────────────────────────────────────┐
│  ← 返回  |  🔬 代码审查专家团                    [编辑] [执行]   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  角色列表                                        [+ 添加角色]    │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  🔍 研究员                                    执行顺序: 1 │   │
│  │  分析代码结构、识别技术栈                                   │   │
│  │  绑定技能: [code-analysis ✓] [file-reader ✓] [+ 绑定]    │   │
│  │                                        [编辑] [删除]      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  🐛 审查员                                    执行顺序: 2 │   │
│  │  发现 Bug、安全漏洞                                        │   │
│  │  依赖: [🔍 研究员]                                        │   │
│  │  绑定技能: [security-scan ✓] [lint-check ✓] [+ 绑定]     │   │
│  │                                        [编辑] [删除]      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ... (更多角色)                                                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 执行进度面板

```
┌─────────────────────────────────────────────────────────────────┐
│  任务执行中...                              [取消] [查看详情]    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  任务: "审查这段代码并修复问题"                                   │
│  专家团: 🔬 代码审查专家团                                        │
│  耗时: 45s                                                      │
│                                                                 │
│  ── 执行进度 ────────────────────────────────────────────────── │
│                                                                 │
│  ✅ 📋 编排完成 — 4个角色，3轮执行                               │
│  │                                                              │
│  ├─ ✅ 🔍 研究员 — 已完成 (12s)                                 │
│  │   ├─ ✅ code-analysis                                        │
│  │   └─ ✅ file-reader                                          │
│  │                                                              │
│  ├─ ✅ 🐛 审查员 — 已完成 (15s)                                 │
│  │   ├─ ✅ security-scan                                        │
│  │   └─ ✅ lint-check                                           │
│  │                                                              │
│  ├─ 🔄 ✍️ 改写者 — 执行中...                                    │
│  │   ├─ ✅ code-edit                                            │
│  │   └─ ⏳ refactor (调用中...)                                  │
│  │                                                              │
│  └─ ⏳ 📝 文档员 — 等待中                                       │
│                                                                 │
│  ── 中间结果 ────────────────────────────────────────────────── │
│                                                                 │
│  🔍 研究员: "识别为 React + TypeScript 项目，使用了 Ant Design..." │
│  🐛 审查员: "发现 3 个安全问题: 1. XSS 风险在..."                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

> 💡 **下一步**：主人确认设计后，我开始写数据库迁移脚本和后端实现代码～ 🌸
