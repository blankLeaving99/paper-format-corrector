"""MySQL 建表 DDL

所有表的 CREATE TABLE 语句，支持幂等执行 (IF NOT EXISTS)。
"""

from __future__ import annotations

# ── 模板库表 ──────────────────────────────────────────────────

TEMPLATE_TABLE = """
CREATE TABLE IF NOT EXISTS `templates` (
    `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `slug` VARCHAR(128) NOT NULL UNIQUE COMMENT '唯一标识符',
    `name` VARCHAR(256) NOT NULL COMMENT '模板显示名称',
    `category` VARCHAR(64) NOT NULL DEFAULT '其他' COMMENT '分类',
    `source` VARCHAR(32) NOT NULL DEFAULT 'personal' COMMENT '来源: bundled/personal/imported/remote',
    `description` TEXT COMMENT '模板描述',
    `config_json` LONGTEXT NOT NULL COMMENT '模板配置 JSON',
    `version` VARCHAR(32) NOT NULL DEFAULT '1.0' COMMENT '语义化版本号',
    `organization` VARCHAR(256) DEFAULT '' COMMENT '所属组织/学校',
    `degree_level` VARCHAR(32) DEFAULT '' COMMENT '学位级别: 本科/硕士/博士',
    `discipline` VARCHAR(64) DEFAULT '' COMMENT '学科',
    `language` VARCHAR(16) DEFAULT '中文' COMMENT '语言',
    `source_url` VARCHAR(512) DEFAULT '' COMMENT '远程来源 URL',
    `tags_json` TEXT COMMENT '标签 JSON 数组',
    `is_active` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否启用',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `remote_id` VARCHAR(128) DEFAULT '' COMMENT '远程同步 ID',
    INDEX `idx_category` (`category`),
    INDEX `idx_source` (`source`),
    INDEX `idx_active` (`is_active`),
    INDEX `idx_created` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='模板库';
"""

# ── 处理报告表 ────────────────────────────────────────────────

REPORT_TABLE = """
CREATE TABLE IF NOT EXISTS `reports` (
    `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `input_file` VARCHAR(512) NOT NULL COMMENT '输入文件名',
    `output_file` VARCHAR(512) DEFAULT '' COMMENT '输出文件路径',
    `preset_name` VARCHAR(64) DEFAULT '' COMMENT '使用的预设名称',
    `template_slug` VARCHAR(128) DEFAULT '' COMMENT '使用的模板 slug',
    `paragraphs_corrected` INT DEFAULT 0 COMMENT '矫正的段落数',
    `headings_fixed` INT DEFAULT 0 COMMENT '修复的标题数',
    `body_fixed` INT DEFAULT 0 COMMENT '修复的正文段落数',
    `quality_score` DECIMAL(5,2) DEFAULT NULL COMMENT '质量评分 0-100',
    `processing_time_ms` INT DEFAULT 0 COMMENT '处理耗时(毫秒)',
    `report_json` LONGTEXT COMMENT '完整报告 JSON',
    `status` VARCHAR(16) NOT NULL DEFAULT 'success' COMMENT '状态: success/error/pending',
    `error_message` TEXT COMMENT '错误信息',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_created` (`created_at`),
    INDEX `idx_status` (`status`),
    INDEX `idx_preset` (`preset_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='处理报告历史';
"""

# ── AI 对话历史表 ─────────────────────────────────────────────

AI_CONVERSATION_TABLE = """
CREATE TABLE IF NOT EXISTS `ai_conversations` (
    `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `session_id` VARCHAR(64) NOT NULL COMMENT '会话 ID',
    `provider` VARCHAR(32) NOT NULL COMMENT 'AI 提供商',
    `model` VARCHAR(64) NOT NULL COMMENT '使用的模型',
    `doc_type` VARCHAR(32) DEFAULT '' COMMENT '文档类型',
    `title` VARCHAR(256) DEFAULT '' COMMENT '文档标题',
    `outline_json` LONGTEXT COMMENT '大纲 JSON',
    `status` VARCHAR(16) NOT NULL DEFAULT 'active' COMMENT '状态: active/completed/abandoned',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_session` (`session_id`),
    INDEX `idx_created` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AI 文档生成会话';
"""

# ── AI 消息表 ─────────────────────────────────────────────────

AI_MESSAGE_TABLE = """
CREATE TABLE IF NOT EXISTS `ai_messages` (
    `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `conversation_id` BIGINT UNSIGNED NOT NULL COMMENT '关联会话 ID',
    `role` VARCHAR(16) NOT NULL COMMENT '角色: user/assistant/system',
    `content` LONGTEXT NOT NULL COMMENT '消息内容',
    `token_count` INT DEFAULT 0 COMMENT 'token 数量',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_conversation` (`conversation_id`),
    FOREIGN KEY (`conversation_id`) REFERENCES `ai_conversations`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AI 对话消息';
"""

# ── 插件注册表 ────────────────────────────────────────────────

PLUGIN_TABLE = """
CREATE TABLE IF NOT EXISTS `plugins` (
    `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(128) NOT NULL UNIQUE COMMENT '插件名称',
    `plugin_type` VARCHAR(32) NOT NULL DEFAULT 'format' COMMENT '类型: format/export/ai/analysis',
    `version` VARCHAR(32) DEFAULT '1.0' COMMENT '版本号',
    `description` TEXT COMMENT '描述',
    `entry_point` VARCHAR(256) DEFAULT '' COMMENT '入口点 (模块路径)',
    `config_json` TEXT COMMENT '配置 JSON',
    `is_enabled` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否启用',
    `installed_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_type` (`plugin_type`),
    INDEX `idx_enabled` (`is_enabled`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='插件注册表';
"""

# ── 格式规则表 ────────────────────────────────────────────────

FORMAT_RULES_TABLE = """
CREATE TABLE IF NOT EXISTS `format_rules` (
    `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `template_slug` VARCHAR(128) NOT NULL COMMENT '关联模板',
    `rule_type` VARCHAR(32) NOT NULL COMMENT '规则类型: font/margin/spacing/numbering',
    `target_section` VARCHAR(64) DEFAULT 'body' COMMENT '目标区域: body/heading1/heading2/reference',
    `rule_json` TEXT NOT NULL COMMENT '规则配置 JSON',
    `priority` INT DEFAULT 100 COMMENT '优先级 (数字越小越优先)',
    `is_active` TINYINT(1) NOT NULL DEFAULT 1,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_template` (`template_slug`),
    INDEX `idx_type` (`rule_type`),
    INDEX `idx_active` (`is_active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='格式规则库';
"""

# ── 系统配置表 ────────────────────────────────────────────────

SETTINGS_TABLE = """
CREATE TABLE IF NOT EXISTS `settings` (
    `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `key` VARCHAR(128) NOT NULL UNIQUE COMMENT '配置键',
    `value` TEXT COMMENT '配置值',
    `value_type` VARCHAR(16) DEFAULT 'string' COMMENT '值类型: string/int/float/json/bool',
    `description` VARCHAR(256) DEFAULT '' COMMENT '描述',
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_key` (`key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统配置';
"""


def get_all_ddl() -> list[str]:
    """获取所有建表 DDL 语句"""
    return [
        TEMPLATE_TABLE,
        REPORT_TABLE,
        AI_CONVERSATION_TABLE,
        AI_MESSAGE_TABLE,
        PLUGIN_TABLE,
        FORMAT_RULES_TABLE,
        SETTINGS_TABLE,
    ]


def initialize_database(db_manager) -> int:
    """初始化数据库：建库建表

    Args:
        db_manager: DatabaseManager 实例

    Returns:
        创建的表数量
    """
    db_manager.create_database_if_not_exists()

    created = 0
    with db_manager.cursor() as cur:
        for ddl in get_all_ddl():
            cur.execute(ddl)
            created += 1

    return created
