"""MySQL 模板仓储实现

基于 MySQL 的模板 CRUD 操作，替代原有 SQLite 实现。
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from .connection import DatabaseManager

logger = logging.getLogger(__name__)


class MySQLTemplateRepository:
    """MySQL 模板仓储

    提供模板的增删改查、导入导出、版本管理等功能。
    """

    def __init__(self, db: DatabaseManager):
        self.db = db

    def save(self, record: dict[str, Any]) -> int:
        """保存或更新模板记录

        Args:
            record: 模板数据字典，必须包含 slug, name, config_json

        Returns:
            记录 ID
        """
        tags_json = json.dumps(record.get("tags", []), ensure_ascii=False)
        config_json = json.dumps(record.get("config", {}), ensure_ascii=False)

        sql = """
            INSERT INTO templates
                (slug, name, category, source, description, config_json, version,
                 organization, degree_level, discipline, language, source_url,
                 tags_json, is_active, remote_id)
            VALUES
                (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                name = VALUES(name),
                category = VALUES(category),
                source = VALUES(source),
                description = VALUES(description),
                config_json = VALUES(config_json),
                version = VALUES(version),
                organization = VALUES(organization),
                degree_level = VALUES(degree_level),
                discipline = VALUES(discipline),
                language = VALUES(language),
                source_url = VALUES(source_url),
                tags_json = VALUES(tags_json),
                is_active = VALUES(is_active),
                remote_id = VALUES(remote_id)
        """
        values = (
            record["slug"],
            record["name"],
            record.get("category", "其他"),
            record.get("source", "personal"),
            record.get("description", ""),
            config_json,
            record.get("version", "1.0"),
            record.get("organization", ""),
            record.get("degree_level", ""),
            record.get("discipline", ""),
            record.get("language", "中文"),
            record.get("source_url", ""),
            tags_json,
            1 if record.get("is_active", True) else 0,
            record.get("remote_id", ""),
        )

        with self.db.cursor() as cur:
            cur.execute(sql, values)
            return cur.lastrowid or 0

    def find_by_slug(self, slug: str) -> dict[str, Any] | None:
        """根据 slug 查找模板"""
        sql = "SELECT * FROM templates WHERE slug = %s LIMIT 1"
        with self.db.cursor() as cur:
            cur.execute(sql, (slug,))
            row = cur.fetchone()
        if row:
            return self._row_to_dict(row)
        return None

    def find_by_id(self, template_id: int) -> dict[str, Any] | None:
        """根据 ID 查找模板"""
        sql = "SELECT * FROM templates WHERE id = %s LIMIT 1"
        with self.db.cursor() as cur:
            cur.execute(sql, (template_id,))
            row = cur.fetchone()
        if row:
            return self._row_to_dict(row)
        return None

    def find_all(
        self,
        category: str | None = None,
        source: str | None = None,
        active_only: bool = True,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """列出模板，支持筛选"""
        conditions = []
        params: list = []

        if category:
            conditions.append("category = %s")
            params.append(category)
        if source:
            conditions.append("source = %s")
            params.append(source)
        if active_only:
            conditions.append("is_active = 1")

        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        sql = f"SELECT * FROM templates {where} ORDER BY created_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        with self.db.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

        return [self._row_to_dict(r) for r in rows]

    def delete(self, slug: str) -> bool:
        """删除模板"""
        sql = "DELETE FROM templates WHERE slug = %s"
        with self.db.cursor() as cur:
            cur.execute(sql, (slug,))
            return cur.rowcount > 0

    def count(self, category: str | None = None, source: str | None = None) -> int:
        """统计模板数量"""
        conditions = []
        params: list = []
        if category:
            conditions.append("category = %s")
            params.append(category)
        if source:
            conditions.append("source = %s")
            params.append(source)

        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        sql = f"SELECT COUNT(*) as cnt FROM templates {where}"

        with self.db.cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
            return row["cnt"] if row else 0

    def exists(self, slug: str) -> bool:
        """检查模板是否存在"""
        sql = "SELECT 1 FROM templates WHERE slug = %s LIMIT 1"
        with self.db.cursor() as cur:
            cur.execute(sql, (slug,))
            return cur.fetchone() is not None

    def search(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        """全文搜索模板"""
        sql = """
            SELECT * FROM templates
            WHERE is_active = 1
              AND (name LIKE %s OR description LIKE %s OR tags_json LIKE %s OR slug LIKE %s)
            ORDER BY updated_at DESC
            LIMIT %s
        """
        pattern = f"%{query}%"
        with self.db.cursor() as cur:
            cur.execute(sql, (pattern, pattern, pattern, pattern, limit))
            rows = cur.fetchall()
        return [self._row_to_dict(r) for r in rows]

    def get_categories(self) -> list[str]:
        """获取所有分类"""
        sql = "SELECT DISTINCT category FROM templates WHERE is_active = 1 ORDER BY category"
        with self.db.cursor() as cur:
            cur.execute(sql)
            return [r["category"] for r in cur.fetchall()]

    def get_sources(self) -> list[str]:
        """获取所有来源类型"""
        sql = "SELECT DISTINCT source FROM templates WHERE is_active = 1 ORDER BY source"
        with self.db.cursor() as cur:
            cur.execute(sql)
            return [r["source"] for r in cur.fetchall()]

    def _row_to_dict(self, row: dict) -> dict[str, Any]:
        """将数据库行转换为业务字典"""
        config = {}
        try:
            config = json.loads(row.get("config_json", "{}"))
        except (json.JSONDecodeError, TypeError):
            pass

        tags = []
        try:
            tags = json.loads(row.get("tags_json", "[]"))
        except (json.JSONDecodeError, TypeError):
            pass

        return {
            "id": row["id"],
            "slug": row["slug"],
            "name": row["name"],
            "category": row["category"],
            "source": row["source"],
            "description": row.get("description", ""),
            "config": config,
            "version": row.get("version", "1.0"),
            "organization": row.get("organization", ""),
            "degree_level": row.get("degree_level", ""),
            "discipline": row.get("discipline", ""),
            "language": row.get("language", "中文"),
            "source_url": row.get("source_url", ""),
            "tags": tags,
            "is_active": bool(row.get("is_active", 1)),
            "created_at": str(row.get("created_at", "")),
            "updated_at": str(row.get("updated_at", "")),
            "remote_id": row.get("remote_id", ""),
        }
