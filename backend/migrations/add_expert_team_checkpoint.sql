-- 专家团执行检查点字段
-- 新增 progress_json 用于断点恢复和执行回放

ALTER TABLE expert_team_run
    ADD COLUMN progress_json JSON NOT NULL DEFAULT (JSON_ARRAY())
    COMMENT '执行检查点记录（断点恢复 + 回放）';
