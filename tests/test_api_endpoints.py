"""API endpoint integration tests.

Tests for the modular FastAPI routes under interfaces/api/.
Covers: health, templates, correct, scan, batch, reports.
"""

from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from paper_format_corrector.interfaces.api.app import app

client = TestClient(app, raise_server_exceptions=False)


# ── Health ────────────────────────────────────────────────────


class TestHealthEndpoint:
    def test_health_returns_ok(self):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert "timestamp" in data

    def test_health_checks_dependencies(self):
        resp = client.get("/api/v1/health")
        data = resp.json()
        assert "checks" in data


# ── Root ──────────────────────────────────────────────────────


class TestRootEndpoint:
    def test_root_returns_service_info(self):
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["service"] == "paper-format-correction"
        assert "docs" in data


# ── Templates ─────────────────────────────────────────────────


class TestTemplatesEndpoints:
    def test_list_templates(self):
        resp = client.get("/api/v1/templates")
        assert resp.status_code == 200
        data = resp.json()
        # API returns paginated dict or list
        assert isinstance(data, (list, dict))

    def test_list_templates_with_category(self):
        resp = client.get("/api/v1/templates?category=ieee")
        assert resp.status_code == 200

    def test_list_templates_with_keyword(self):
        resp = client.get("/api/v1/templates?keyword=apa")
        assert resp.status_code == 200

    def test_get_template_categories(self):
        resp = client.get("/api/v1/templates/categories")
        assert resp.status_code == 200

    def test_get_nonexistent_template(self):
        resp = client.get("/api/v1/templates/nonexistent_template_slug_12345")
        assert resp.status_code == 404


# ── Presets ───────────────────────────────────────────────────


class TestPresetsEndpoint:
    def test_list_presets_via_legacy_api(self):
        """Presets are served via the legacy api/app.py /presets endpoint."""
        from fastapi.testclient import TestClient as LegacyClient
        from paper_format_corrector.interfaces.api.app import app as legacy_app
        legacy_client = LegacyClient(legacy_app, raise_server_exceptions=False)
        resp = legacy_client.get("/presets")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_presets_contain_required_fields(self):
        from fastapi.testclient import TestClient as LegacyClient
        from paper_format_corrector.interfaces.api.app import app as legacy_app
        legacy_client = LegacyClient(legacy_app, raise_server_exceptions=False)
        resp = legacy_client.get("/presets")
        data = resp.json()
        for preset in data:
            assert "name" in preset


# ── Scan ──────────────────────────────────────────────────────


class TestScanEndpoint:
    def test_scan_requires_file(self):
        resp = client.post("/api/v1/scan")
        assert resp.status_code == 422  # Unprocessable Entity

    def test_scan_rejects_non_docx(self):
        fake_file = io.BytesIO(b"not a docx file")
        resp = client.post(
            "/api/v1/scan",
            files={"file": ("test.txt", fake_file, "text/plain")},
        )
        # Should return 400 or handle gracefully
        assert resp.status_code in (400, 422, 500)

    def test_scan_accepts_docx(self):
        sample = Path("tests/fixtures/sample_paper.docx")
        if not sample.exists():
            pytest.skip("sample_paper.docx not found")
        with open(sample, "rb") as f:
            resp = client.post(
                "/api/v1/scan",
                files={"file": ("sample_paper.docx", f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "elements" in data or "structure" in data or "paragraphs" in data


# ── Correct ───────────────────────────────────────────────────


class TestCorrectEndpoint:
    def test_correct_requires_file(self):
        resp = client.post("/api/v1/correct")
        assert resp.status_code == 422

    def test_correct_rejects_non_docx(self):
        fake_file = io.BytesIO(b"not a docx file")
        resp = client.post(
            "/api/v1/correct",
            files={"file": ("test.txt", fake_file, "text/plain")},
        )
        assert resp.status_code in (400, 422, 500)

    def test_correct_accepts_docx_with_preset(self):
        sample = Path("tests/fixtures/sample_paper.docx")
        if not sample.exists():
            pytest.skip("sample_paper.docx not found")
        with open(sample, "rb") as f:
            resp = client.post(
                "/api/v1/correct",
                files={"file": ("sample_paper.docx", f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
                data={"preset": "ieee"},
            )
        assert resp.status_code == 200


# ── Batch ─────────────────────────────────────────────────────


class TestBatchEndpoint:
    def test_batch_requires_files(self):
        resp = client.post("/api/v1/batch")
        assert resp.status_code == 422

    def test_batch_rejects_empty_files(self):
        resp = client.post(
            "/api/v1/batch",
            files=[],
        )
        assert resp.status_code in (400, 422)

    def test_batch_processes_valid_files(self):
        sample = Path("tests/fixtures/sample_paper.docx")
        if not sample.exists():
            pytest.skip("sample_paper.docx not found")
        with open(sample, "rb") as f:
            resp = client.post(
                "/api/v1/batch",
                files=[("files", ("sample_paper.docx", f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document"))],
                data={"preset": "ieee"},
            )
        assert resp.status_code == 200
        # Response should be a zip file
        assert resp.headers.get("content-type") == "application/zip" or b"PK" in resp.content


# ── Reports ───────────────────────────────────────────────────


class TestReportsEndpoints:
    def test_list_reports(self):
        resp = client.get("/api/v1/reports")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_list_reports_with_limit(self):
        resp = client.get("/api/v1/reports?limit=10")
        assert resp.status_code == 200

    def test_get_nonexistent_report(self):
        resp = client.get("/api/v1/reports/999999")
        assert resp.status_code == 404


# ── OpenAPI / Docs ────────────────────────────────────────────


class TestOpenAPI:
    def test_openapi_json_available(self):
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        data = resp.json()
        assert "openapi" in data
        assert "paths" in data

    def test_swagger_ui_available(self):
        resp = client.get("/docs")
        assert resp.status_code == 200

    def test_redoc_available(self):
        resp = client.get("/redoc")
        assert resp.status_code == 200

    def test_all_routes_registered(self):
        resp = client.get("/openapi.json")
        paths = resp.json()["paths"]
        expected = [
            "/api/v1/health",
            "/api/v1/templates",
            "/api/v1/correct",
            "/api/v1/scan",
            "/api/v1/batch",
            "/api/v1/reports",
        ]
        for ep in expected:
            assert ep in paths, f"Missing endpoint: {ep}"


# ── Task Queue (Legacy API) ───────────────────────────────────


class TestTaskQueueEndpoints:
    """Tests for task queue endpoints on the legacy api/app.py."""

    @pytest.fixture(autouse=True)
    def _legacy_client(self):
        from fastapi.testclient import TestClient as LegacyClient
        from paper_format_corrector.interfaces.api.app import app as legacy_app, get_task_queue
        # Reset the global task queue before each test
        import paper_format_corrector.interfaces.api.app as app_module
        app_module._task_queue = None
        app_module._worker = None
        self.client = LegacyClient(legacy_app, raise_server_exceptions=False)
        self._get_queue = get_task_queue

    def test_submit_task_returns_task_id(self):
        resp = self.client.post("/tasks/submit", json={
            "file_path": "test_paper.docx",
            "filename": "test_paper.docx",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "task_id" in data
        assert data["status"] == "pending"

    def test_get_task_status_returns_404_for_missing(self):
        resp = self.client.get("/tasks/nonexistent-task-id")
        assert resp.status_code == 404

    def test_submit_then_get_status(self):
        # Submit a task
        resp = self.client.post("/tasks/submit", json={
            "file_path": "test_paper.docx",
            "filename": "test_paper.docx",
        })
        assert resp.status_code == 200
        task_id = resp.json()["task_id"]

        # Query status - the queue should be the same global instance
        queue = self._get_queue()
        status = queue.get_status(task_id)
        assert status.get("error") is None or "error" not in status
        assert status["task_id"] == task_id
        assert status["status"] in ("pending", "processing", "completed", "failed")

    def test_list_tasks(self):
        # Submit a task
        self.client.post("/tasks/submit", json={
            "file_path": "test_paper.docx",
            "filename": "test_paper.docx",
        })

        resp = self.client.get("/tasks")
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "tasks" in data
        assert data["total"] >= 1

    def test_list_tasks_with_status_filter(self):
        resp = self.client.get("/tasks?status=pending")
        assert resp.status_code == 200
        data = resp.json()
        for t in data["tasks"]:
            assert t["status"] == "pending"

    def test_remove_nonexistent_task_returns_404(self):
        resp = self.client.delete("/tasks/nonexistent-task-id")
        assert resp.status_code == 404

    def test_get_result_for_nonexistent_returns_404(self):
        resp = self.client.get("/tasks/nonexistent-task-id/result")
        assert resp.status_code == 404
