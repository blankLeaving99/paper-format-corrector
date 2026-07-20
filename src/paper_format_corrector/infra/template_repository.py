"""Local SQLite repository for built-in and user-created paper templates.

Supports versioning, tags, import/export, metadata, and template management
as specified in the project requirements (zhinan.md section 3.3).
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from .preset_loader import list_presets, load_preset


@dataclass(frozen=True)
class TemplateRecord:
    slug: str
    name: str
    category: str
    source: str
    description: str
    config: dict[str, Any]
    version: str = "1.0"
    organization: str = ""
    degree_level: str = ""
    discipline: str = ""
    language: str = "中文"
    source_url: str = ""
    tags: list[str] = field(default_factory=list)
    is_active: bool = True
    created_at: str = ""
    updated_at: str = ""


class TemplateRepository:
    """Stores reusable style profiles with versioning, tags, and import/export."""

    SCHEMA_VERSION = 3

    def __init__(self, database_path: str | Path | None = None):
        self.database_path = Path(database_path or Path("data") / "template_library.db")
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS paper_templates (
                    slug TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    source TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    config_json TEXT NOT NULL,
                    version TEXT NOT NULL DEFAULT '1.0',
                    organization TEXT NOT NULL DEFAULT '',
                    degree_level TEXT NOT NULL DEFAULT '',
                    discipline TEXT NOT NULL DEFAULT '',
                    language TEXT NOT NULL DEFAULT '中文',
                    source_url TEXT NOT NULL DEFAULT '',
                    source_file_hash TEXT NOT NULL DEFAULT '',
                    verified_at TEXT,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            connection.execute("CREATE INDEX IF NOT EXISTS idx_template_category ON paper_templates(category)")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_template_source ON paper_templates(source)")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_template_organization ON paper_templates(organization)")

            connection.execute("""
                CREATE TABLE IF NOT EXISTS template_tags (
                    slug TEXT NOT NULL,
                    tag TEXT NOT NULL,
                    PRIMARY KEY (slug, tag),
                    FOREIGN KEY (slug) REFERENCES paper_templates(slug) ON DELETE CASCADE
                )
            """)

            connection.execute("""
                CREATE TABLE IF NOT EXISTS template_versions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    slug TEXT NOT NULL,
                    version TEXT NOT NULL,
                    config_json TEXT NOT NULL,
                    changelog TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (slug) REFERENCES paper_templates(slug) ON DELETE CASCADE
                )
            """)

            connection.execute("""
                CREATE TABLE IF NOT EXISTS template_usage_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    slug TEXT NOT NULL,
                    used_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (slug) REFERENCES paper_templates(slug) ON DELETE CASCADE
                )
            """)

            connection.execute("""
                CREATE TABLE IF NOT EXISTS processing_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    input_file TEXT NOT NULL,
                    output_file TEXT NOT NULL DEFAULT '',
                    template_used TEXT NOT NULL DEFAULT '',
                    quality_score REAL NOT NULL DEFAULT 0,
                    total_elements INTEGER NOT NULL DEFAULT 0,
                    modified_elements INTEGER NOT NULL DEFAULT 0,
                    processing_time REAL NOT NULL DEFAULT 0,
                    report_json TEXT NOT NULL DEFAULT '{}',
                    status TEXT NOT NULL DEFAULT 'success',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            connection.execute("CREATE INDEX IF NOT EXISTS idx_history_created ON processing_history(created_at)")

            connection.execute("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER NOT NULL
                )
            """)
            cur = connection.execute("SELECT version FROM schema_version")
            row = cur.fetchone()
            if row is None:
                connection.execute("INSERT INTO schema_version (version) VALUES (?)", (self.SCHEMA_VERSION,))
            elif row[0] < self.SCHEMA_VERSION:
                self._migrate(connection, row[0])
                connection.execute("UPDATE schema_version SET version = ?", (self.SCHEMA_VERSION,))

        self.seed_builtin_templates()

    def _migrate(self, connection: sqlite3.Connection, from_version: int) -> None:
        if from_version < 2:
            try:
                connection.execute("ALTER TABLE paper_templates ADD COLUMN version TEXT NOT NULL DEFAULT '1.0'")
                connection.execute("ALTER TABLE paper_templates ADD COLUMN organization TEXT NOT NULL DEFAULT ''")
                connection.execute("ALTER TABLE paper_templates ADD COLUMN degree_level TEXT NOT NULL DEFAULT ''")
                connection.execute("ALTER TABLE paper_templates ADD COLUMN discipline TEXT NOT NULL DEFAULT ''")
                connection.execute("ALTER TABLE paper_templates ADD COLUMN language TEXT NOT NULL DEFAULT '中文'")
                connection.execute("ALTER TABLE paper_templates ADD COLUMN source_url TEXT NOT NULL DEFAULT ''")
                connection.execute("ALTER TABLE paper_templates ADD COLUMN source_file_hash TEXT NOT NULL DEFAULT ''")
                connection.execute("ALTER TABLE paper_templates ADD COLUMN verified_at TEXT")
                connection.execute("ALTER TABLE paper_templates ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1")
            except sqlite3.OperationalError:
                pass
        if from_version < 3:
            try:
                connection.execute("""
                    CREATE TABLE IF NOT EXISTS processing_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        input_file TEXT NOT NULL,
                        output_file TEXT NOT NULL DEFAULT '',
                        template_used TEXT NOT NULL DEFAULT '',
                        quality_score REAL NOT NULL DEFAULT 0,
                        total_elements INTEGER NOT NULL DEFAULT 0,
                        modified_elements INTEGER NOT NULL DEFAULT 0,
                        processing_time REAL NOT NULL DEFAULT 0,
                        report_json TEXT NOT NULL DEFAULT '{}',
                        status TEXT NOT NULL DEFAULT 'success',
                        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                connection.execute("CREATE INDEX IF NOT EXISTS idx_history_created ON processing_history(created_at)")
            except sqlite3.OperationalError:
                pass

    def seed_builtin_templates(self) -> None:
        for preset in list_presets():
            slug = f"builtin-{preset['name']}"
            with self._connect() as connection:
                exists = connection.execute("SELECT 1 FROM paper_templates WHERE slug = ?", (slug,)).fetchone()
                if exists:
                    continue
                config = load_preset(preset["name"])
                connection.execute(
                    """INSERT INTO paper_templates
                       (slug, name, category, source, description, config_json, version, organization, language)
                       VALUES (?, ?, ?, 'bundled', ?, ?, '1.0', ?, ?)""",
                    (slug, preset["name"], _infer_category(preset["name"]),
                     preset["description"], json.dumps(config, ensure_ascii=False),
                     _infer_organization(preset["name"]), _infer_language(preset["name"])),
                )
                self._save_version(connection, slug, "1.0", json.dumps(config, ensure_ascii=False), "初始版本")

    def list_templates(
        self,
        category: str | None = None,
        source: str | None = None,
        organization: str | None = None,
        language: str | None = None,
        active_only: bool = True,
    ) -> list[TemplateRecord]:
        query = "SELECT slug, name, category, source, description, config_json, version, organization, degree_level, discipline, language, source_url, is_active, created_at, updated_at FROM paper_templates"
        conditions: list[str] = []
        params: list[str] = []
        if category:
            conditions.append("category = ?")
            params.append(category)
        if source:
            conditions.append("source = ?")
            params.append(source)
        if organization:
            conditions.append("organization = ?")
            params.append(organization)
        if language:
            conditions.append("language = ?")
            params.append(language)
        if active_only:
            conditions.append("is_active = 1")
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY category, source DESC, name"
        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._record_with_meta(row, connection=self._connect()) for row in rows]

    def search_templates(self, keyword: str) -> list[TemplateRecord]:
        like = f"%{keyword}%"
        query = """SELECT slug, name, category, source, description, config_json, version,
                   organization, degree_level, discipline, language, source_url, is_active,
                   created_at, updated_at FROM paper_templates
                   WHERE is_active = 1 AND (name LIKE ? OR description LIKE ? OR organization LIKE ? OR category LIKE ?)
                   ORDER BY category, name"""
        with self._connect() as connection:
            rows = connection.execute(query, (like, like, like, like)).fetchall()
        return [self._record_with_meta(row, connection=self._connect()) for row in rows]

    def get(self, slug: str) -> TemplateRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                """SELECT slug, name, category, source, description, config_json, version,
                   organization, degree_level, discipline, language, source_url, is_active,
                   created_at, updated_at FROM paper_templates WHERE slug = ?""",
                (slug,),
            ).fetchone()
        return self._record_with_meta(row, connection=self._connect()) if row else None

    def save_personal_template(
        self,
        name: str,
        category: str,
        config: dict[str, Any],
        description: str = "",
        tags: list[str] | None = None,
        organization: str = "",
        degree_level: str = "",
        discipline: str = "",
        language: str = "中文",
    ) -> TemplateRecord:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("模板名称不能为空")
        slug = f"personal-{_slugify(clean_name)}"
        payload = json.dumps(config, ensure_ascii=False)
        now = datetime.now().isoformat()
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO paper_templates
                   (slug, name, category, source, description, config_json, version,
                    organization, degree_level, discipline, language, created_at, updated_at)
                   VALUES (?, ?, ?, 'personal', ?, ?, '1.0', ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(slug) DO UPDATE SET
                    category=excluded.category, description=excluded.description,
                    config_json=excluded.config_json, organization=excluded.organization,
                    degree_level=excluded.degree_level, discipline=excluded.discipline,
                    language=excluded.language, updated_at=excluded.updated_at""",
                (slug, clean_name, category or "personal", description, payload,
                 organization, degree_level, discipline, language, now, now),
            )
            self._save_version(connection, slug, "1.0", payload, "创建模板")
            if tags:
                self._set_tags(connection, slug, tags)
        return TemplateRecord(
            slug=slug, name=clean_name, category=category or "personal",
            source="personal", description=description, config=config,
            organization=organization, degree_level=degree_level,
            discipline=discipline, language=language,
        )

    def update_template(self, slug: str, updates: dict[str, Any]) -> TemplateRecord | None:
        existing = self.get(slug)
        if existing is None:
            return None
        if existing.source == "bundled":
            raise ValueError("内置模板不能直接修改，请先复制为个人模板")
        fields: list[str] = []
        params: list[str] = []
        for key in ("name", "category", "description", "organization", "degree_level", "discipline", "language", "source_url"):
            if key in updates:
                fields.append(f"{key} = ?")
                params.append(str(updates[key]))
        if "config" in updates:
            fields.append("config_json = ?")
            params.append(json.dumps(updates["config"], ensure_ascii=False))
        if "is_active" in updates:
            fields.append("is_active = ?")
            params.append(1 if updates["is_active"] else 0)
        if not fields:
            return existing
        fields.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        params.append(slug)
        with self._connect() as connection:
            connection.execute(f"UPDATE paper_templates SET {', '.join(fields)} WHERE slug = ?", params)
            if "config" in updates:
                version = existing.version
                parts = version.split(".")
                if len(parts) == 2:
                    try:
                        version = f"{parts[0]}.{int(parts[1]) + 1}"
                    except ValueError:
                        pass
                self._save_version(connection, slug, version, json.dumps(updates["config"], ensure_ascii=False), updates.get("changelog", ""))
                connection.execute("UPDATE paper_templates SET version = ? WHERE slug = ?", (version, slug))
            if "tags" in updates:
                self._set_tags(connection, slug, updates["tags"])
        return self.get(slug)

    def delete_template(self, slug: str) -> bool:
        with self._connect() as connection:
            row = connection.execute("SELECT source FROM paper_templates WHERE slug = ?", (slug,)).fetchone()
            if row is None:
                return False
            if row["source"] == "bundled":
                connection.execute("UPDATE paper_templates SET is_active = 0 WHERE slug = ?", (slug,))
                return True
            connection.execute("DELETE FROM template_tags WHERE slug = ?", (slug,))
            connection.execute("DELETE FROM template_versions WHERE slug = ?", (slug,))
            connection.execute("DELETE FROM template_usage_logs WHERE slug = ?", (slug,))
            connection.execute("DELETE FROM paper_templates WHERE slug = ?", (slug,))
            return True

    def enable_template(self, slug: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE paper_templates SET is_active = 1 WHERE slug = ? AND is_active = 0",
                (slug,),
            )
            return cursor.rowcount > 0

    def copy_template(self, source_slug: str, new_name: str, new_category: str | None = None) -> TemplateRecord | None:
        source = self.get(source_slug)
        if source is None:
            return None
        return self.save_personal_template(
            name=new_name,
            category=new_category or source.category,
            config=source.config,
            description=f"复制自: {source.name}",
            tags=list(source.tags),
            organization=source.organization,
            degree_level=source.degree_level,
            discipline=source.discipline,
            language=source.language,
        )

    def get_versions(self, slug: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT version, config_json, changelog, created_at FROM template_versions WHERE slug = ? ORDER BY created_at DESC",
                (slug,),
            ).fetchall()
        return [{"version": r["version"], "config": json.loads(r["config_json"]), "changelog": r["changelog"], "created_at": r["created_at"]} for r in rows]

    def get_tags(self, slug: str) -> list[str]:
        with self._connect() as connection:
            rows = connection.execute("SELECT tag FROM template_tags WHERE slug = ?", (slug,)).fetchall()
        return [r["tag"] for r in rows]

    # ========== 处理历史管理 ==========

    def save_processing_history(
        self,
        input_file: str,
        output_file: str,
        template_used: str = "",
        quality_score: float = 0.0,
        total_elements: int = 0,
        modified_elements: int = 0,
        processing_time: float = 0.0,
        report: dict | None = None,
        status: str = "success",
    ) -> int:
        """保存一条处理记录，返回记录ID"""
        report_json = json.dumps(report or {}, ensure_ascii=False)
        with self._connect() as connection:
            cursor = connection.execute(
                """INSERT INTO processing_history
                   (input_file, output_file, template_used, quality_score,
                    total_elements, modified_elements, processing_time,
                    report_json, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (input_file, output_file, template_used, quality_score,
                 total_elements, modified_elements, processing_time,
                 report_json, status),
            )
            return cursor.lastrowid or 0

    def list_processing_history(self, limit: int = 50) -> list[dict]:
        """列出最近的处理记录"""
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT id, input_file, output_file, template_used,
                   quality_score, total_elements, modified_elements,
                   processing_time, status, created_at
                   FROM processing_history
                   ORDER BY created_at DESC LIMIT ?""",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_processing_history(self, record_id: int) -> dict | None:
        """获取单条处理记录详情"""
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM processing_history WHERE id = ?", (record_id,)
            ).fetchone()
        if row is None:
            return None
        result = dict(row)
        result["report"] = json.loads(result.pop("report_json", "{}"))
        return result

    def delete_processing_history(self, record_id: int) -> bool:
        """删除单条处理记录"""
        with self._connect() as connection:
            connection.execute("DELETE FROM processing_history WHERE id = ?", (record_id,))
            return connection.total_changes > 0

    def record_usage(self, slug: str) -> None:
        with self._connect() as connection:
            connection.execute("INSERT INTO template_usage_logs (slug) VALUES (?)", (slug,))

    def import_from_yaml(self, file_path: str | Path) -> TemplateRecord:
        import yaml
        path = Path(file_path)
        with open(path, encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
        name = config.pop("name", path.stem)
        description = config.pop("description", "")
        category = config.pop("category", "导入模板")
        return self.save_personal_template(
            name=name, category=category, config=config,
            description=description, language=_detect_language(config),
        )

    def import_from_json(self, file_path: str | Path) -> TemplateRecord:
        path = Path(file_path)
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        name = data.pop("name", path.stem)
        description = data.pop("description", "")
        category = data.pop("category", "导入模板")
        return self.save_personal_template(
            name=name, category=category, config=data,
            description=description, language=_detect_language(data),
        )

    def export_to_yaml(self, slug: str, output_path: str | Path) -> Path:
        import yaml
        record = self.get(slug)
        if record is None:
            raise ValueError(f"模板不存在: {slug}")
        data = {"name": record.name, "description": record.description, "category": record.category, **record.config}
        output = Path(output_path)
        with open(output, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        return output

    def export_to_json(self, slug: str, output_path: str | Path) -> Path:
        record = self.get(slug)
        if record is None:
            raise ValueError(f"模板不存在: {slug}")
        data = {
            "name": record.name, "description": record.description,
            "category": record.category, "version": record.version,
            "organization": record.organization, "language": record.language,
            **record.config,
        }
        output = Path(output_path)
        with open(output, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return output

    def _save_version(self, connection: sqlite3.Connection, slug: str, version: str, config_json: str, changelog: str) -> None:
        connection.execute(
            "INSERT INTO template_versions (slug, version, config_json, changelog) VALUES (?, ?, ?, ?)",
            (slug, version, config_json, changelog),
        )

    def _set_tags(self, connection: sqlite3.Connection, slug: str, tags: list[str]) -> None:
        connection.execute("DELETE FROM template_tags WHERE slug = ?", (slug,))
        for tag in tags:
            tag = tag.strip()
            if tag:
                connection.execute("INSERT INTO template_tags (slug, tag) VALUES (?, ?)", (slug, tag))

    def _record_with_meta(self, row: sqlite3.Row, connection: sqlite3.Connection | None = None) -> TemplateRecord:
        tags: list[str] = []
        if connection:
            tag_rows = connection.execute("SELECT tag FROM template_tags WHERE slug = ?", (row["slug"],)).fetchall()
            tags = [r["tag"] for r in tag_rows]
        return TemplateRecord(
            slug=row["slug"], name=row["name"], category=row["category"],
            source=row["source"], description=row["description"],
            config=json.loads(row["config_json"]),
            version=row["version"] if "version" in row.keys() else "1.0",
            organization=row["organization"] if "organization" in row.keys() else "",
            degree_level=row["degree_level"] if "degree_level" in row.keys() else "",
            discipline=row["discipline"] if "discipline" in row.keys() else "",
            language=row["language"] if "language" in row.keys() else "中文",
            source_url=row["source_url"] if "source_url" in row.keys() else "",
            tags=tags,
            is_active=bool(row["is_active"]) if "is_active" in row.keys() else True,
            created_at=row["created_at"] if "created_at" in row.keys() else "",
            updated_at=row["updated_at"] if "updated_at" in row.keys() else "",
        )

    @staticmethod
    def _record(row: sqlite3.Row) -> TemplateRecord:
        return TemplateRecord(
            slug=row["slug"], name=row["name"], category=row["category"],
            source=row["source"], description=row["description"],
            config=json.loads(row["config_json"]),
        )


def _infer_category(name: str) -> str:
    if name in {"chinese_thesis"}:
        return "高校毕业论文"
    if name in {"apa", "mla", "chicago", "harvard"}:
        return "引用与写作规范"
    return "国际期刊与会议"


def _infer_organization(name: str) -> str:
    orgs = {
        "ieee": "IEEE", "nature": "Nature", "science": "Science",
        "apa": "APA", "mla": "MLA", "chicago": "Chicago",
        "harvard": "Harvard", "elsevier": "Elsevier",
        "acm": "ACM", "springer": "Springer",
    }
    return orgs.get(name, "")


def _infer_language(name: str) -> str:
    if name == "chinese_thesis":
        return "中文"
    return "英文"


def _detect_language(config: dict) -> str:
    font_rules = config.get("format_rules", {}).get("font", {})
    cn_font = font_rules.get("chinese", "")
    if cn_font and any(c in cn_font for c in "宋体黑体楷体仿宋"):
        return "中文"
    return "英文"


def _slugify(value: str) -> str:
    result = "".join(char.lower() if char.isalnum() else "-" for char in value).strip("-")
    return result or "template"
