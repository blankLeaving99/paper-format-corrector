"""MySQL 报告仓储实现

存储矫正处理报告历史，支持统计分析和分页查询。
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any

from .connection import DatabaseManager

logger = logging.getLogger(__name__)


class MySQLReportRepository:
    """MySQL 报告仓储

    存储每次矫正处理的报告，支持统计查询。
    """

    def __init__(self, db: DatabaseManager):
        self.db = db

    def save(self, report: dict[str, Any]) -> int:
        """保存处理报告

        Args:
            report: 报告数据字典

        Returns:
            记录 ID
        """
        report_json = json.dumps(report, ensure_ascii=False, default=str)

        sql = """
            INSERT INTO reports
                (input_file, output_file, preset_name, template_slug,
                 paragraphs_corrected, headings_fixed, body_fixed,
                 quality_score, processing_time_ms, report_json,
                 status, error_message)
            VALUES
                (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (
            report.get("input_file", ""),
            report.get("output_file", ""),
            report.get("preset_name", ""),
            report.get("template_slug", ""),
            report.get("paragraphs_corrected", 0),
            report.get("headings_fixed", 0),
            report.get("body_fixed", 0),
            report.get("quality_score"),
            report.get("processing_time_ms", 0),
            report_json,
            report.get("status", "success"),
            report.get("error_message", ""),
        )

        with self.db.cursor() as cur:
            cur.execute(sql, values)
            return cur.lastrowid or 0

    def find_by_id(self, report_id: int) -> dict[str, Any] | None:
        """根据 ID 查找报告"""
        sql = "SELECT * FROM reports WHERE id = %s LIMIT 1"
        with self.db.cursor() as cur:
            cur.execute(sql, (report_id,))
            row = cur.fetchone()
        if row:
            return self._row_to_dict(row)
        return None

    def find_all(
        self,
        status: str | None = None,
        preset_name: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """列出报告，支持筛选和分页"""
        conditions = []
        params: list = []

        if status:
            conditions.append("status = %s")
            params.append(status)
        if preset_name:
            conditions.append("preset_name = %s")
            params.append(preset_name)

        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        sql = f"SELECT * FROM reports {where} ORDER BY created_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        with self.db.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

        return [self._row_to_dict(r) for r in rows]

    def delete(self, report_id: int) -> bool:
        """删除报告"""
        sql = "DELETE FROM reports WHERE id = %s"
        with self.db.cursor() as cur:
            cur.execute(sql, (report_id,))
            return cur.rowcount > 0

    def count(self, status: str | None = None) -> int:
        """统计报告数量"""
        if status:
            sql = "SELECT COUNT(*) as cnt FROM reports WHERE status = %s"
            params = (status,)
        else:
            sql = "SELECT COUNT(*) as cnt FROM reports"
            params = ()

        with self.db.cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
            return row["cnt"] if row else 0

    def get_statistics(self, days: int = 30) -> dict[str, Any]:
        """获取统计信息

        Args:
            days: 统计最近多少天

        Returns:
            统计数据字典
        """
        since = datetime.now() - timedelta(days=days)

        sql = """
            SELECT
                COUNT(*) as total_reports,
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_count,
                SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as error_count,
                AVG(quality_score) as avg_quality_score,
                AVG(processing_time_ms) as avg_processing_time,
                SUM(paragraphs_corrected) as total_paragraphs,
                MAX(quality_score) as max_quality_score
            FROM reports
            WHERE created_at >= %s
        """

        with self.db.cursor() as cur:
            cur.execute(sql, (since,))
            row = cur.fetchone()

        if not row:
            return {}

        return {
            "period_days": days,
            "total_reports": row["total_reports"] or 0,
            "success_count": row["success_count"] or 0,
            "error_count": row["error_count"] or 0,
            "success_rate": (
                round(row["success_count"] / row["total_reports"] * 100, 1)
                if row["total_reports"] else 0
            ),
            "avg_quality_score": round(float(row["avg_quality_score"] or 0), 1),
            "avg_processing_time_ms": round(float(row["avg_processing_time"] or 0), 0),
            "total_paragraphs_corrected": row["total_paragraphs"] or 0,
            "max_quality_score": float(row["max_quality_score"] or 0),
        }

    def get_preset_usage(self, limit: int = 10) -> list[dict[str, Any]]:
        """获取预设使用频率排行"""
        sql = """
            SELECT preset_name, COUNT(*) as usage_count,
                   AVG(quality_score) as avg_score
            FROM reports
            WHERE preset_name != '' AND status = 'success'
            GROUP BY preset_name
            ORDER BY usage_count DESC
            LIMIT %s
        """
        with self.db.cursor() as cur:
            cur.execute(sql, (limit,))
            return cur.fetchall()

    def _row_to_dict(self, row: dict) -> dict[str, Any]:
        """将数据库行转换为业务字典"""
        report_data = {}
        try:
            report_data = json.loads(row.get("report_json", "{}"))
        except (json.JSONDecodeError, TypeError):
            pass

        return {
            "id": row["id"],
            "input_file": row["input_file"],
            "output_file": row.get("output_file", ""),
            "preset_name": row.get("preset_name", ""),
            "template_slug": row.get("template_slug", ""),
            "paragraphs_corrected": row.get("paragraphs_corrected", 0),
            "headings_fixed": row.get("headings_fixed", 0),
            "body_fixed": row.get("body_fixed", 0),
            "quality_score": float(row["quality_score"]) if row.get("quality_score") else None,
            "processing_time_ms": row.get("processing_time_ms", 0),
            "status": row.get("status", "success"),
            "error_message": row.get("error_message", ""),
            "created_at": str(row.get("created_at", "")),
            "report": report_data,
        }
