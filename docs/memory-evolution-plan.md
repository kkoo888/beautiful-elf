# 记忆模块进化方案

## Context

beautiful-elf 项目的记忆系统已迭代到 v5.0（四大进化版），具备 ACT-R 认知衰减、Cross-Encoder Rerank、4路并行检索+RRF融合、实体关系图谱、信念演化+仲裁、Episode 经历等能力，在开源领域已属上乘。

通过调研 2026 业内最前沿技术（MAGMA ACL 2026、Letta Sleep-Time Compute、Mem0 55k stars、Zep/Graphiti 时序知识图谱、Cognee、Cloudflare Agent Memory），识别出 3 个高影响差距和多个中等优先级改进点。本方案聚焦**渐进增强**而非推翻重建。

---

## 差距分析矩阵

| 能力维度 | 当前 (v5.0) | 前沿对标 | 差距 |
|----------|-------------|----------|------|
| 多信号检索 | 4路: 语义+BM25+标签图+时间 | MAGMA 3图正交 | **中** — 实体图未接入检索管线 |
| Cross-Encoder Rerank | ONNX 本地推理 | 业内标配 | **已具备** |
| ACT-R 认知衰减 | 完整公式+dormant+动态半衰期 | 业内少有 | **已超越** |
| RRF+MMR | 标准实现 | Hindsight TEMPR | **已具备** |
| 信念演化+仲裁 | reinforce/weaken/contradict | Hindsight CARA | **已具备** |
| Episode bi-temporal | Episode 级别 | Zep Graphiti | **部分** — 实体关系边无 valid_at |
| 实体图谱 | 完整抽取+消歧+关系 | Mem0 Entity Linking | **部分** — 抽取完整但检索未利用 |
| Sleep-Time Compute | 无 | Letta MemGPT 2.0 | **缺失** |
| 记忆合并去重 | 仅 expert_team | Mem0/Zep | **缺失** — 主集合碎片堆积 |
| 记忆过时检测 | 无自动机制 | 业内开放问题 | **缺失** |
| Procedural Memory | 无 | Mem0/Cloudflare | **缺失** |
| 异步写入 | 部分 fire-and-forget | Mem0 async-default | **部分** |
| Multi-Scope | 仅 user_id | Mem0 4层 scope | **缺失**（单用户场景非刚需） |
| 网络分类 4类 | world/experience/opinion/observation | Hindsight | **已具备** |
| Token 预算 | 自适应填充 | 最佳实践 | **已具备** |
| 多跳推理 | 不支持 | MAGMA 跨图遍历 | **缺失** |

---

## 进化路线图

### 阶段 1: Quick Win（1-2 周）

#### Task 1.1 实体图接入检索管线 (Channel 5) — ROI ★★★★★

**问题**: `MemoryEntity` + `MemoryEntityRelation` 已有完整数据模型和 LLM 抽取流水线，但未接入 `search_with_scores()` 检索管线。

**方案**:
- 在 `memory_manager.py` 的 `search_with_scores()` 新增 Channel 5: 实体图遍历
- 流程: query 提取实体名 → 匹配 MemoryEntity → 通过 Relation 找关联实体 → 用 name/aliases 扩展 Qdrant 检索
- 结果合入 RRF 融合

**涉及文件**:
- `backend/app/agent/memory_manager.py` — 新增 Channel 5 + `_extract_query_entities()` + `_expand_entity_neighbors()`
- `backend/app/repository/memory_entity_repo.py` — 新增按名称模糊匹配 + 邻居查询

**预期收益**: 实体关联记忆召回率 +20-30%

---

#### Task 1.2 Observation 新鲜度自动衰减 — ROI ★★★☆☆

**问题**: `Observation.freshness` 仅在 `distill()` 时由 LLM 判断初始值，之后永不变更。

**方案**:
- 新增定时任务 `observation_freshness_sweep()`（每周执行）
- 规则: new >14天 → stable; stable >60天无新证据 → weakening; weakening >30天 → stale
- stale observation 在检索时降权（score * 0.5）

**涉及文件**:
- `backend/app/services/markdown_memory_service.py` — 新增 `sweep_freshness()`
- `backend/app/tasks/memory_tasks.py` — 新增定时任务
- `backend/app/repository/observation_repo.py` — 新增批量查询

---

#### Task 1.3 记忆写入异步化 — ROI ★★★★☆

**问题**: `save_summary()` 内 LLM 摘要 + embedding 串行执行，可能阻塞响应。

**方案**:
- `save_summary()` 拆分为 `enqueue_summary()` + `_process_summary()`
- Redis list 作写入 buffer，Celery task 异步消费

**涉及文件**:
- `backend/app/agent/memory_manager.py` — 拆分方法
- `backend/app/tasks/memory_tasks.py` — 新增 task

**预期收益**: 对话响应延迟 -200~500ms

---

### 阶段 2: 中期（3-6 周）

#### Task 2.1 Sleep-Time Compute Agent — ROI ★★★★★（最高）

**问题**: 当前记忆系统"只存不整理"。Qdrant 中 detail/summary 持续堆积，缺乏深度整理。Letta 证明 sleep-time compute 是从"碎片记忆"到"结构化知识"的关键跃迁。

**方案**: 新增 `SleepTimeAgent` 后台处理管线，每日凌晨执行
- **Phase A 碎片合并**: 扫描近7天 detail/summary，LLM 判断合并
- **Phase B 知识图谱更新**: 新 summary 执行实体+关系抽取
- **Phase C 洞察触发**: 发现矛盾/新模式时自动触发 `reflect()`
- 可配置更强模型（`SLEEPTIME_MODEL`）

**涉及文件**:
- 新增 `backend/app/agent/sleeptime_agent.py`
- 新增 `backend/app/services/memory_consolidation_service.py`
- `backend/app/tasks/memory_tasks.py` — 新增 `sleeptime_consolidation`
- `backend/app/agent/memory_manager.py` — 新增 `list_unconsolidated()` / `mark_consolidated()`

**预期收益**: Qdrant 碎片 -40~60%，检索质量显著提升

---

#### Task 2.2 主记忆集合合并去重 — ROI ★★★★☆

**方案**: 将 `_consolidate()` 抽象为通用 `MemoryConsolidationService`，`save_summary()` 写入前检索相似度 >0.85 执行合并决策

**涉及文件**:
- 新增 `backend/app/services/memory_consolidation_service.py`
- `backend/app/agent/memory_manager.py` — `save_summary()` 增加合并检查
- `backend/app/agent/expert_team/memory.py` — `_consolidate()` 迁移

---

#### Task 2.3 实体关系时间维度 (Bi-Temporal Edge) — ROI ★★★☆☆

**方案**: `MemoryEntityRelation` 新增 `valid_at` / `invalid_at` 字段，实体抽取时 LLM 推断时间性，冲突自动检测

**涉及文件**:
- `backend/app/models/memory_entity_relation.py` — 新增字段
- `backend/alembic/versions/` — 迁移脚本
- `backend/app/services/markdown_memory_service.py` — `extract_entities()` 增加时间推断

---

### 阶段 3: 长期（6-12 周）

#### Task 3.1 MAGMA 风格多图检索 — ROI ★★★☆☆
构建三层正交图（语义图+时间图+实体图），新增 Channel 6 跨图遍历。依赖 Task 1.1 + 2.1

#### Task 3.2 记忆过时检测 (Staleness Detection) — ROI ★★★☆☆
`StalenessDetector` 服务，每周扫描标记 `staleness_score`，高分触发 LLM 验证。依赖 Task 2.1

#### Task 3.3 Procedural Memory — ROI ★★☆☆☆
新增 `MemoryProcedure` 模型，从成功 episode 自动提取标准化操作步骤。依赖 Task 2.1

---

## Top 5 推荐（按 ROI 排序）

| # | 进化项 | ROI | 理由 |
|---|--------|-----|------|
| 1 | **Sleep-Time Compute Agent** | ★★★★★ | 解决最核心"只存不整理"问题，所有长期进化的前置依赖 |
| 2 | **实体图接入检索管线** | ★★★★★ | 数据模型 100% 就绪，仅需接入检索，投入最小收益立竿见影 |
| 3 | **主记忆合并去重** | ★★★★☆ | 直接解决碎片堆积，复用 expert_team 已验证逻辑 |
| 4 | **记忆写入异步化** | ★★★★☆ | 直接影响 UX（延迟 -200~500ms） |
| 5 | **Observation 新鲜度衰减** | ★★★☆☆ | 投入极低，解决逻辑漏洞 |

---

## 不推荐做

| 项目 | 原因 |
|------|------|
| 引入 Cognee | 已有完整实体图谱，Cognee 面向文档管理非对话记忆 |
| Mem0 多 Scope | 单用户桌面 Agent 不需要 4 层 scope |
| Cloudflare 8-Check | 记忆来源可信度高，Cross-Encoder + ACT-R 已够 |
| Markdown 双向同步 | 已有完整 Markdown 体系，人工审核单用户收益有限 |
| 完全替换 MAGMA/Zep | 应渐进增加 Channel，不推翻重建 |

---

## 验证方式

1. **Task 1.1**: 20 条含实体关联的测试 query，对比 Channel 5 前后召回率
2. **Task 1.2**: 创建 observation 后改 created_at 到 30 天前，运行 sweep 验证状态变更
3. **Task 1.3**: 对话结束时计时，对比异步化前后响应延迟
4. **Task 2.1**: 50 条模拟 detail/summary，运行 SleepTimeAgent 验证合并率 >40%
5. **Task 2.2**: 5 条相似度 >0.85 的 summary，验证合并决策触发
6. **Task 2.3**: 两条 works_at 关系（不同公司+不同时间），验证 invalid_at 自动设置
