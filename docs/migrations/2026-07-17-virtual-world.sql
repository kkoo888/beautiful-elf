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


-- ─────────────────────────────────────────────────────────────
-- 4. 方块类型初始数据
-- ─────────────────────────────────────────────────────────────

INSERT INTO `virtual_world_block` (`block_id`, `name`, `category`, `geometry_type`, `geometry_args`, `default_material`, `description`, `tags`, `sort_order`) VALUES
('cube',        '方块',   'structure',   'box',        '{"width":1,"height":1,"depth":1}',                                    'concrete',  '基础积木',   'basic,building',    0),
('wall',        '墙壁',   'structure',   'box',        '{"width":1,"height":3,"depth":0.2}',                                 'brick',     '墙体',      'building,wall',     1),
('floor',       '地板',   'structure',   'box',        '{"width":1,"height":0.1,"depth":1}',                                 'wood',      '地面',      'building,floor',    2),
('roof_slope',  '斜屋顶', 'structure',   'cone',       '{"radius":0.7,"height":1,"segments":4}',                             'brick',     '屋顶',      'building,roof',     3),
('roof_flat',   '平屋顶', 'structure',   'box',        '{"width":1,"height":0.1,"depth":1}',                                 'concrete',  '平屋顶',    'building,roof',     4),
('pillar',      '柱子',   'structure',   'cylinder',   '{"radiusTop":0.15,"radiusBottom":0.15,"height":3,"segments":16}',  'concrete',  '支撑柱',    'building,support',  5),
('stairs',      '楼梯',   'structure',   'box',        '{"width":1,"height":0.25,"depth":0.5}',                             'wood',      '台阶',      'building,stairs',   6),
('window',      '窗户',   'structure',   'box',        '{"width":0.8,"height":1,"depth":0.05}',                             'glass',     '透明窗',    'building,window',   7),
('tree_trunk',  '树干',   'decoration',  'cylinder',   '{"radiusTop":0.1,"radiusBottom":0.1,"height":2,"segments":8}',     'wood',      '树干',      'nature,tree',       8),
('tree_canopy', '树冠',   'decoration',  'sphere',     '{"radius":0.8,"widthSegments":16,"heightSegments":12}',              'grass',     '树叶',      'nature,tree',       9),
('bush',        '灌木',   'decoration',  'sphere',     '{"radius":0.4,"widthSegments":12,"heightSegments":8}',               'grass',     '绿植',      'nature,bush',       10),
('flower',      '花朵',   'nature',      'cylinder',   '{"radiusTop":0.05,"radiusBottom":0.15,"height":0.3,"segments":8}', 'neon_pink', '装饰花',    'nature,flower',     11),
('rock',        '石头',   'decoration',  'dodecahedron','{"radius":0.3,"detail":0}',                                         'concrete',  '自然石块',  'nature,rock',       12),
('fence',       '栅栏',   'decoration',  'box',        '{"width":1,"height":0.8,"depth":0.05}',                            'wood',      '围栏',      'decoration,fence',  13),
('lamp_post',   '路灯',   'light',       'cylinder',   '{"radiusTop":0.03,"radiusBottom":0.03,"height":3,"segments":8}',   'metal',     '街灯',      'light,street',      14),
('chair',       '椅子',   'furniture',   'box',        '{"width":0.5,"height":0.5,"depth":0.5}',                           'wood',      '坐具',      'furniture,seat',    15),
('table',       '桌子',   'furniture',   'box',        '{"width":1,"height":0.8,"depth":0.6}',                             'wood',      '台面',      'furniture,table',   16),
('bed',         '床',     'furniture',   'box',        '{"width":2,"height":0.4,"depth":1}',                               'wood',      '睡眠',      'furniture,bed',     17),
('bookshelf',   '书架',   'furniture',   'box',        '{"width":1,"height":2,"depth":0.3}',                               'wood',      '存储',      'furniture,storage', 18),
('sofa',        '沙发',   'furniture',   'box',        '{"width":1.5,"height":0.6,"depth":0.8}',                           'wood',      '座椅',      'furniture,seat',    19),
('desk',        '书桌',   'furniture',   'box',        '{"width":1.2,"height":0.75,"depth":0.6}',                          'wood',      '工作',      'furniture,work',    20),
('water',       '水面',   'nature',      'plane',      '{"width":1,"height":1}',                                            'water',     '水池/湖',   'nature,water',      21),
('grass_block', '草地',   'nature',      'plane',      '{"width":1,"height":1}',                                            'grass',     '地面',      'nature,ground',     22),
('sand',        '沙地',   'nature',      'plane',      '{"width":1,"height":1}',                                            'sand',      '沙滩',      'nature,ground',     23),
('snow',        '雪地',   'nature',      'plane',      '{"width":1,"height":1}',                                            'snow',      '冬季',      'nature,ground',     24);
