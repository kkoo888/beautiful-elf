-- ═══════════════════════════════════════════════════════════════
-- 虚拟世界模块 — 数据库迁移脚本
-- 日期：2026-07-17
-- 对应文档：agent-3d-building-block-system.md §3.8
-- 严格遵循 MySQL P3C 规范
-- ═══════════════════════════════════════════════════════════════

-- ─────────────────────────────────────────────────────────────
-- 1. 虚拟世界场景表
-- ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS `virtual_world_scene` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `name` varchar(128) NOT NULL DEFAULT '' COMMENT '场景名称',
  `description` varchar(500) NOT NULL DEFAULT '' COMMENT '场景描述',
  `width` int unsigned NOT NULL DEFAULT '32' COMMENT '场景宽度（网格单位）',
  `depth` int unsigned NOT NULL DEFAULT '32' COMMENT '场景深度（网格单位）',
  `height` int unsigned NOT NULL DEFAULT '16' COMMENT '场景高度（网格单位）',
  `ambient_color` varchar(16) NOT NULL DEFAULT '#ffffff' COMMENT '环境光颜色',
  `sky_color` varchar(16) NOT NULL DEFAULT '#87ceeb' COMMENT '天空颜色',
  `time_of_day` int unsigned NOT NULL DEFAULT '12' COMMENT '时间(0-24)',
  `is_active` tinyint unsigned NOT NULL DEFAULT '0' COMMENT '是否激活: 1=是 0=否',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `is_deleted` tinyint unsigned NOT NULL DEFAULT '0' COMMENT '是否删除: 1=是 0=否',
  PRIMARY KEY (`id`),
  KEY `idx_virtual_world_scene_is_active` (`is_active`),
  KEY `idx_virtual_world_scene_is_deleted` (`is_deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ─────────────────────────────────────────────────────────────
-- 2. 虚拟世界方块类型注册表
-- ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS `virtual_world_block` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `block_id` varchar(64) NOT NULL DEFAULT '' COMMENT '方块ID（如 cube, wall, tree）',
  `name` varchar(128) NOT NULL DEFAULT '' COMMENT '方块名称',
  `category` varchar(32) NOT NULL DEFAULT 'structure' COMMENT '分类: structure/decoration/nature/furniture/light/road',
  `geometry_type` varchar(32) NOT NULL DEFAULT 'box' COMMENT '几何体类型: box/cylinder/sphere/cone/plane',
  `geometry_args` json NOT NULL DEFAULT (JSON_OBJECT()) COMMENT '几何体参数 JSON',
  `default_material` varchar(64) NOT NULL DEFAULT 'default' COMMENT '默认材质ID',
  `description` varchar(500) NOT NULL DEFAULT '' COMMENT '描述',
  `tags` varchar(500) NOT NULL DEFAULT '' COMMENT '标签(逗号分隔)',
  `sort_order` int unsigned NOT NULL DEFAULT '0' COMMENT '排序',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `is_deleted` tinyint unsigned NOT NULL DEFAULT '0' COMMENT '是否删除: 1=是 0=否',
  PRIMARY KEY (`id`),
  KEY `idx_virtual_world_block_block_id` (`block_id`),
  KEY `idx_virtual_world_block_category` (`category`),
  KEY `idx_virtual_world_block_is_deleted` (`is_deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ─────────────────────────────────────────────────────────────
-- 3. 场景方块实例表
-- ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS `virtual_world_scene_block` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `scene_id` bigint unsigned NOT NULL COMMENT '场景ID',
  `block_id` varchar(64) NOT NULL DEFAULT '' COMMENT '方块类型ID',
  `pos_x` int NOT NULL DEFAULT '0' COMMENT 'X坐标（可为负）',
  `pos_y` int NOT NULL DEFAULT '0' COMMENT 'Y坐标（可为负）',
  `pos_z` int NOT NULL DEFAULT '0' COMMENT 'Z坐标（可为负）',
  `rotation_y` int unsigned NOT NULL DEFAULT '0' COMMENT 'Y轴旋转(0/90/180/270)',
  `material` varchar(64) NOT NULL DEFAULT '' COMMENT '材质覆盖(空=默认)',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `is_deleted` tinyint unsigned NOT NULL DEFAULT '0' COMMENT '是否删除: 1=是 0=否',
  PRIMARY KEY (`id`),
  KEY `idx_virtual_world_scene_block_scene_id` (`scene_id`),
  KEY `idx_virtual_world_scene_block_block_id` (`block_id`),
  KEY `idx_virtual_world_scene_block_is_deleted` (`is_deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
