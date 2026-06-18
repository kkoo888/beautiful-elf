-- 专家团 v2 字段扩展
-- 执行时间: 2026-06-18
-- 说明: 借鉴 CrewAI Agent/Task 属性，增强专家团能力

-- ─── ExpertTeam 新增字段 ───
ALTER TABLE expert_team
    ADD COLUMN process_mode VARCHAR(16) NOT NULL DEFAULT 'parallel' COMMENT '执行模式: parallel=并行 sequential=顺序' AFTER max_rounds;

-- ─── Expert 新增字段 ───
ALTER TABLE expert
    ADD COLUMN goal TEXT NOT NULL DEFAULT '' COMMENT '专家目标 — 驱动决策方向' AFTER avatar,
    ADD COLUMN backstory TEXT NOT NULL DEFAULT '' COMMENT '专家背景 — 丰富角色人格' AFTER goal,
    ADD COLUMN allow_delegation INT NOT NULL DEFAULT 0 COMMENT '允许委派: 1=是 0=否' AFTER tools_json,
    ADD COLUMN max_execution_time INT NOT NULL DEFAULT 120 COMMENT '最大执行时间（秒）' AFTER allow_delegation;
