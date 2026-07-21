"""Tests for collaborative template synchronization.

Covers:
- RemoteTemplateClient pull/push operations
- Offline degradation
- Conflict resolution (timestamp-based)
- API sync endpoints
- TemplateRepository remote_id support
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from typing import Any

import pytest

from paper_format_corrector.infra.remote_template_client import RemoteTemplateClient
from paper_format_corrector.infra.template_repository import TemplateRepository

# ── Helpers ──────────────────────────────────────────────────────


def _make_remote_server(tmp_path, db_name: str = "remote_server.db"):
    """Create a mock remote template server for testing.

    Uses a raw SQLite connection (no TemplateRepository seeding) to avoid
    pulling in all built-in presets during tests.
    """
    import sqlite3 as _sqlite3

    db_path = tmp_path / db_name

    # Ensure the schema exists (same DDL as TemplateRepository._initialize)
    _init_db = _sqlite3.connect(str(db_path))
    _init_db.execute("""
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
            remote_id TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    _init_db.commit()
    _init_db.close()

    class Handler(BaseHTTPRequestHandler):
        def _get_conn(self):
            conn = _sqlite3.connect(str(db_path))
            conn.row_factory = _sqlite3.Row
            return conn

        def do_GET(self):
            if self.path == "/health":
                self._json_response(200, {"status": "ok"})
            elif self.path == "/api/v1/templates/sync/list":
                conn = self._get_conn()
                try:
                    rows = conn.execute(
                        "SELECT slug, name, category, organization, version, "
                        "config_json, remote_id, updated_at FROM paper_templates "
                        "WHERE is_active = 1"
                    ).fetchall()
                    items = []
                    for r in rows:
                        remote_id = r["remote_id"] if "remote_id" in r.keys() else ""
                        if not remote_id:
                            continue
                        items.append({
                            "id": remote_id,
                            "slug": r["slug"],
                            "name": r["name"],
                            "category": r["category"],
                            "organization": r["organization"],
                            "version": r["version"],
                            "config": json.loads(r["config_json"]),
                            "tags": [],
                            "is_public": "true",
                            "updated_at": r["updated_at"],
                        })
                    self._json_response(200, items)
                finally:
                    conn.close()
            elif self.path.startswith("/api/v1/templates/sync/"):
                remote_id = self.path.split("/")[-1]
                conn = self._get_conn()
                try:
                    row = conn.execute(
                        "SELECT slug, name, category, organization, version, "
                        "config_json, description, remote_id, created_at, updated_at "
                        "FROM paper_templates WHERE remote_id = ?",
                        (remote_id,),
                    ).fetchone()
                    if row is None:
                        self._json_response(404, {"detail": "not found"})
                    else:
                        self._json_response(200, {
                            "id": row["remote_id"],
                            "slug": row["slug"],
                            "name": row["name"],
                            "category": row["category"],
                            "organization": row["organization"],
                            "version": row["version"],
                            "config": json.loads(row["config_json"]),
                            "description": row["description"],
                            "tags": [],
                            "is_public": "true",
                            "created_at": row["created_at"],
                            "updated_at": row["updated_at"],
                        })
                finally:
                    conn.close()
            else:
                self._json_response(404, {"detail": "not found"})

        def do_POST(self):
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            payload = json.loads(body) if body else {}

            if self.path == "/api/v1/templates/sync/push":
                name = payload.get("name", "")
                config = payload.get("config", {})
                remote_id = str(uuid.uuid4())
                conn = self._get_conn()
                try:
                    slug = f"personal-{name.lower().replace(' ', '-')}"
                    conn.execute(
                        "INSERT INTO paper_templates "
                        "(slug, name, category, source, description, config_json, "
                        "version, organization, remote_id, is_active, created_at, updated_at) "
                        "VALUES (?, ?, ?, 'personal', ?, ?, '1.0', ?, ?, 1, datetime('now'), datetime('now'))",
                        (slug, name, payload.get("category", "remote"),
                         payload.get("description", ""), json.dumps(config, ensure_ascii=False),
                         payload.get("organization", ""), remote_id),
                    )
                    conn.commit()
                    self._json_response(200, {"id": remote_id, "slug": slug, "name": name})
                finally:
                    conn.close()
            elif self.path.startswith("/api/v1/templates/sync/"):
                remote_id = self.path.split("/")[-1]
                conn = self._get_conn()
                try:
                    row = conn.execute(
                        "SELECT slug FROM paper_templates WHERE remote_id = ?", (remote_id,)
                    ).fetchone()
                    if row is None:
                        self._json_response(404, {"detail": "not found"})
                    else:
                        if "config" in payload:
                            conn.execute(
                                "UPDATE paper_templates SET config_json = ?, updated_at = datetime('now') WHERE slug = ?",
                                (json.dumps(payload["config"], ensure_ascii=False), row["slug"]),
                            )
                            conn.commit()
                        self._json_response(200, {
                            "id": remote_id,
                            "slug": row["slug"],
                            "updated_at": datetime.now().isoformat(),
                        })
                finally:
                    conn.close()
            else:
                self._json_response(404, {"detail": "not found"})

        def _json_response(self, code: int, data: Any):
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

        def log_message(self, format, *args):
            pass  # suppress noisy logs

    server = HTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, port


def _seed_server_templates(remote_db: TemplateRepository, count: int = 3) -> list[str]:
    """Seed the remote server DB with test templates. Returns list of remote_ids."""
    import sqlite3 as _sqlite3

    remote_ids = []
    for i in range(count):
        name = f"Remote Template {i}"
        record = remote_db.save_personal_template(
            name=name,
            category="remote_test",
            config={"format_rules": {"body_text": {"font_size": 12 + i}}},
            description=f"Test template {i}",
            tags=[f"tag{i}"],
            organization="TestOrg",
        )
        rid = str(uuid.uuid4())
        # Use raw SQL to set remote_id (avoids seed_builtin_templates interference)
        conn = _sqlite3.connect(str(remote_db.database_path))
        try:
            conn.execute("UPDATE paper_templates SET remote_id = ? WHERE slug = ?", (rid, record.slug))
            conn.commit()
        finally:
            conn.close()
        remote_ids.append(rid)
    return remote_ids


# ── RemoteTemplateClient tests ───────────────────────────────────


class TestRemoteTemplateClientPull:
    def test_pull_list_returns_templates(self, tmp_path):
        """pull_list should return template dicts from the remote server."""
        remote_db = TemplateRepository(tmp_path / "server.db")
        _seed_server_templates(remote_db, 2)

        server, port = _make_remote_server(tmp_path, "server.db")
        try:
            client = RemoteTemplateClient(f"http://127.0.0.1:{port}")
            items = client.pull_list()
            assert isinstance(items, list)
            assert len(items) >= 2
        finally:
            server.shutdown()

    def test_pull_template_by_id(self, tmp_path):
        """pull_template should return a single template by remote_id."""
        remote_db = TemplateRepository(tmp_path / "server.db")
        rids = _seed_server_templates(remote_db, 1)

        server, port = _make_remote_server(tmp_path, "server.db")
        try:
            client = RemoteTemplateClient(f"http://127.0.0.1:{port}")
            result = client.pull_template(rids[0])
            assert result is not None
            assert result["name"] == "Remote Template 0"
        finally:
            server.shutdown()

    def test_pull_all_adds_new_templates(self, tmp_path):
        """pull_all should create new personal templates locally."""
        remote_db = TemplateRepository(tmp_path / "server.db")
        _seed_server_templates(remote_db, 2)

        local_db = TemplateRepository(tmp_path / "local.db")
        server, port = _make_remote_server(tmp_path, "server.db")
        try:
            client = RemoteTemplateClient(f"http://127.0.0.1:{port}")
            added = client.pull_all(local_db)
            assert len(added) == 2
            local_templates = local_db.list_templates(source="personal")
            assert len(local_templates) == 2
            for t in local_templates:
                assert local_db.get_remote_id(t.slug) != ""
        finally:
            server.shutdown()

    def test_pull_all_skips_existing(self, tmp_path):
        """pull_all should not duplicate templates already pulled."""
        remote_db = TemplateRepository(tmp_path / "server.db")
        _seed_server_templates(remote_db, 1)

        local_db = TemplateRepository(tmp_path / "local.db")
        server, port = _make_remote_server(tmp_path, "server.db")
        try:
            client = RemoteTemplateClient(f"http://127.0.0.1:{port}")
            client.pull_all(local_db)
            # Pull again — should add nothing
            added_again = client.pull_all(local_db)
            assert len(added_again) == 0
            local_templates = local_db.list_templates(source="personal")
            assert len(local_templates) == 1
        finally:
            server.shutdown()


class TestRemoteTemplateClientPush:
    def test_push_template_creates_remote(self, tmp_path):
        """push_template should send the local template to the remote."""
        local_db = TemplateRepository(tmp_path / "local.db")
        saved = local_db.save_personal_template(
            "Push Test", "test", {"format_rules": {}}, tags=["push"]
        )

        server, port = _make_remote_server(tmp_path)
        try:
            client = RemoteTemplateClient(f"http://127.0.0.1:{port}")
            remote_id = client.push_template(local_db, saved.slug)
            assert remote_id is not None
            assert local_db.get_remote_id(saved.slug) == remote_id
        finally:
            server.shutdown()

    def test_push_all_pushes_unsynced(self, tmp_path):
        """push_all should only push templates without a remote_id."""
        local_db = TemplateRepository(tmp_path / "local.db")
        local_db.save_personal_template("P1", "test", {"format_rules": {}})
        local_db.save_personal_template("P2", "test", {"format_rules": {}})

        server, port = _make_remote_server(tmp_path)
        try:
            client = RemoteTemplateClient(f"http://127.0.0.1:{port}")
            pushed = client.push_all(local_db)
            assert len(pushed) == 2
            # Second push_all should push nothing
            pushed_again = client.push_all(local_db)
            assert len(pushed_again) == 0
        finally:
            server.shutdown()


class TestConflictResolution:
    def test_remote_wins_when_newer(self, tmp_path):
        """When remote updated_at > local updated_at, remote config wins."""
        local_config = {"format_rules": {"body_text": {"font_size": 10}}}
        remote_config = {"format_rules": {"body_text": {"font_size": 14}}}
        merged = RemoteTemplateClient._resolve_conflict(
            local_config, remote_config,
            "2024-01-01T00:00:00", "2024-06-01T00:00:00",
        )
        assert merged["format_rules"]["body_text"]["font_size"] == 14

    def test_local_wins_when_local_is_newer(self, tmp_path):
        """When local updated_at > remote updated_at, local config wins."""
        local_config = {"format_rules": {"body_text": {"font_size": 10}}}
        remote_config = {"format_rules": {"body_text": {"font_size": 14}}}
        merged = RemoteTemplateClient._resolve_conflict(
            local_config, remote_config,
            "2024-06-01T00:00:00", "2024-01-01T00:00:00",
        )
        assert merged["format_rules"]["body_text"]["font_size"] == 10


class TestOfflineDegradation:
    def test_pull_list_returns_empty_when_offline(self, tmp_path):
        """When the server is unreachable, pull_list should return empty list."""
        client = RemoteTemplateClient("http://127.0.0.1:1")  # port 1 = unreachable
        result = client.pull_list()
        assert result == []

    def test_pull_template_returns_none_when_offline(self, tmp_path):
        """When the server is unreachable, pull_template should return None."""
        client = RemoteTemplateClient("http://127.0.0.1:1")
        result = client.pull_template("any-id")
        assert result is None

    def test_push_template_returns_none_when_offline(self, tmp_path):
        """When the server is unreachable, push_template should return None."""
        local_db = TemplateRepository(tmp_path / "local.db")
        saved = local_db.save_personal_template("Offline Test", "test", {"format_rules": {}})
        client = RemoteTemplateClient("http://127.0.0.1:1")
        result = client.push_template(local_db, saved.slug)
        assert result is None

    def test_is_online_returns_false_when_offline(self):
        """is_online should return False when the server is unreachable."""
        client = RemoteTemplateClient("http://127.0.0.1:1")
        assert client.is_online() is False

    def test_push_all_returns_empty_when_offline(self, tmp_path):
        """push_all should return empty list when server is unreachable."""
        local_db = TemplateRepository(tmp_path / "local.db")
        local_db.save_personal_template("Offline Push", "test", {"format_rules": {}})
        client = RemoteTemplateClient("http://127.0.0.1:1")
        result = client.push_all(local_db)
        assert result == []


# ── TemplateRepository remote_id tests ──────────────────────────


class TestTemplateRepositoryRemoteId:
    def test_set_and_get_remote_id(self, tmp_path):
        """set_remote_id and get_remote_id should work correctly."""
        repo = TemplateRepository(tmp_path / "test.db")
        saved = repo.save_personal_template("Remote ID Test", "test", {"format_rules": {}})
        assert repo.get_remote_id(saved.slug) == ""

        remote_id = str(uuid.uuid4())
        repo.set_remote_id(saved.slug, remote_id)
        assert repo.get_remote_id(saved.slug) == remote_id

    def test_find_by_remote_id(self, tmp_path):
        """find_by_remote_id should return the matching template."""
        repo = TemplateRepository(tmp_path / "test.db")
        saved = repo.save_personal_template("Find By Remote", "test", {"format_rules": {}})
        remote_id = str(uuid.uuid4())
        repo.set_remote_id(saved.slug, remote_id)

        found = repo.find_by_remote_id(remote_id)
        assert found is not None
        assert found.slug == saved.slug

    def test_find_by_remote_id_returns_none(self, tmp_path):
        """find_by_remote_id should return None for unknown ID."""
        repo = TemplateRepository(tmp_path / "test.db")
        assert repo.find_by_remote_id("nonexistent") is None

    def test_find_by_remote_id_empty_string(self, tmp_path):
        """find_by_remote_id should return None for empty string."""
        repo = TemplateRepository(tmp_path / "test.db")
        assert repo.find_by_remote_id("") is None

    def test_list_personal_templates(self, tmp_path):
        """list_personal_templates should only return personal templates."""
        repo = TemplateRepository(tmp_path / "test.db")
        repo.save_personal_template("Personal 1", "test", {"format_rules": {}})
        repo.save_personal_template("Personal 2", "test", {"format_rules": {}})
        personal = repo.list_personal_templates()
        assert len(personal) >= 2
        assert all(t.source == "personal" for t in personal)


# ── API sync endpoint tests (FastAPI TestClient) ────────────────


class TestSyncEndpoints:
    def _get_app(self):
        from fastapi import FastAPI

        from paper_format_corrector.interfaces.api.routes.templates import router

        app = FastAPI()
        app.include_router(router)
        return app

    def test_sync_list_endpoint(self, tmp_path):
        """GET /api/v1/templates/sync/list should return template list."""
        try:
            from fastapi.testclient import TestClient
        except ImportError:
            pytest.skip("fastapi[testclient] not installed")

        app = self._get_app()
        client = TestClient(app)
        response = client.get("/api/v1/templates/sync/list")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_sync_push_endpoint(self, tmp_path):
        """POST /api/v1/templates/sync/push should create a template and return remote ID."""
        try:
            from fastapi.testclient import TestClient
        except ImportError:
            pytest.skip("fastapi[testclient] not installed")

        app = self._get_app()
        client = TestClient(app)
        payload = {
            "name": "Sync Push Test",
            "category": "sync_test",
            "config": {"format_rules": {"body_text": {"font_size": 12}}},
            "tags": ["sync"],
        }
        response = client.post("/api/v1/templates/sync/push", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["name"] == "Sync Push Test"

    def test_sync_push_empty_name_fails(self, tmp_path):
        """POST /api/v1/templates/sync/push with empty name should return 400."""
        try:
            from fastapi.testclient import TestClient
        except ImportError:
            pytest.skip("fastapi[testclient] not installed")

        app = self._get_app()
        client = TestClient(app)
        response = client.post("/api/v1/templates/sync/push", json={"name": "", "config": {}})
        assert response.status_code == 400

    def test_sync_update_endpoint(self, tmp_path):
        """POST /api/v1/templates/sync/{remote_id} should update an existing template."""
        try:
            from fastapi.testclient import TestClient
        except ImportError:
            pytest.skip("fastapi[testclient] not installed")

        app = self._get_app()
        client = TestClient(app)
        # First push a template
        push_resp = client.post("/api/v1/templates/sync/push", json={
            "name": "To Update",
            "category": "test",
            "config": {"format_rules": {}},
        })
        remote_id = push_resp.json()["id"]

        # Then update it
        update_resp = client.post(f"/api/v1/templates/sync/{remote_id}", json={
            "name": "Updated Name",
            "config": {"format_rules": {"body_text": {"font_size": 14}}},
        })
        assert update_resp.status_code == 200
        assert update_resp.json()["name"] == "Updated Name"

    def test_sync_get_nonexistent_returns_404(self, tmp_path):
        """GET /api/v1/templates/sync/{id} with unknown ID should return 404."""
        try:
            from fastapi.testclient import TestClient
        except ImportError:
            pytest.skip("fastapi[testclient] not installed")

        app = self._get_app()
        client = TestClient(app)
        response = client.get("/api/v1/templates/sync/nonexistent-id")
        assert response.status_code == 404
