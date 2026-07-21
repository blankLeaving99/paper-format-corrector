"""Tests for template sync service (check_updates, pull_updates, offline fallback)."""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

from paper_format_corrector.adapters.storage.template_repository import (
    TemplateRepository,
    _parse_version,
    _version_is_newer,
)
from paper_format_corrector.adapters.template_sync import TemplateSyncService

# ------------------------------------------------------------------
# Helper function tests
# ------------------------------------------------------------------


class TestParseVersion:
    def test_valid_version(self):
        assert _parse_version("2.1") == (2, 1)

    def test_single_number(self):
        assert _parse_version("3") == (3,)

    def test_three_parts(self):
        assert _parse_version("1.0.3") == (1, 0, 3)

    def test_invalid_returns_zero(self):
        assert _parse_version("invalid") == (0,)

    def test_empty_string(self):
        assert _parse_version("") == (0,)

    def test_strips_whitespace(self):
        assert _parse_version("  2.1  ") == (2, 1)

    def test_non_numeric_part_stops(self):
        assert _parse_version("2.abc") == (2,)


class TestVersionIsNewer:
    def test_newer(self):
        assert _version_is_newer("2.0", "1.0") is True

    def test_same(self):
        assert _version_is_newer("1.0", "1.0") is False

    def test_older(self):
        assert _version_is_newer("1.0", "2.0") is False

    def test_minor_upgrade(self):
        assert _version_is_newer("1.2", "1.1") is True

    def test_patch_upgrade(self):
        assert _version_is_newer("1.0.1", "1.0.0") is True

    def test_local_empty_always_newer(self):
        assert _version_is_newer("1.0", "") is True


# ------------------------------------------------------------------
# TemplateSyncService.check_updates tests
# ------------------------------------------------------------------


class TestCheckUpdates:
    def test_no_remote_url_returns_empty(self, tmp_path):
        repo = TemplateRepository(tmp_path / "templates.db")
        service = TemplateSyncService(repo, remote_url="")
        assert service.check_updates() == []

    def test_identifies_new_template(self, tmp_path):
        repo = TemplateRepository(tmp_path / "templates.db")
        service = TemplateSyncService(repo, remote_url="https://example.com/templates")

        manifest = {
            "new-template": {"name": "New Template", "version": "1.0"},
        }
        with patch.object(service, "_fetch_manifest", return_value=manifest):
            updates = service.check_updates()

        assert len(updates) == 1
        assert updates[0]["id"] == "new-template"
        assert updates[0]["action"] == "new"

    def test_identifies_update_needed(self, tmp_path):
        repo = TemplateRepository(tmp_path / "templates.db")
        # Save a personal template with remote ID "test-tpl" at version 1.0
        repo.save_remote_template(
            template_id="test-tpl",
            name="Test Template",
            category="test",
            config={"format_rules": {}},
            version="1.0",
        )

        service = TemplateSyncService(repo, remote_url="https://example.com/templates")
        manifest = {
            "test-tpl": {"name": "Test Template", "version": "2.0"},
        }
        with patch.object(service, "_fetch_manifest", return_value=manifest):
            updates = service.check_updates()

        assert len(updates) == 1
        assert updates[0]["action"] == "update"
        assert updates[0]["from_version"] == "1.0"
        assert updates[0]["to_version"] == "2.0"

    def test_no_update_when_versions_match(self, tmp_path):
        repo = TemplateRepository(tmp_path / "templates.db")
        repo.save_remote_template(
            template_id="test-tpl",
            name="Test Template",
            category="test",
            config={"format_rules": {}},
            version="1.0",
        )

        service = TemplateSyncService(repo, remote_url="https://example.com/templates")
        manifest = {
            "test-tpl": {"name": "Test Template", "version": "1.0"},
        }
        with patch.object(service, "_fetch_manifest", return_value=manifest):
            updates = service.check_updates()

        assert updates == []

    def test_manifest_fetch_failure_returns_empty(self, tmp_path):
        repo = TemplateRepository(tmp_path / "templates.db")
        service = TemplateSyncService(repo, remote_url="https://example.com/templates")

        with patch.object(service, "_fetch_manifest", return_value=None):
            updates = service.check_updates()

        assert updates == []

    def test_no_update_when_remote_older(self, tmp_path):
        repo = TemplateRepository(tmp_path / "templates.db")
        repo.save_remote_template(
            template_id="test-tpl",
            name="Test Template",
            category="test",
            config={"format_rules": {}},
            version="3.0",
        )

        service = TemplateSyncService(repo, remote_url="https://example.com/templates")
        manifest = {
            "test-tpl": {"name": "Test Template", "version": "2.0"},
        }
        with patch.object(service, "_fetch_manifest", return_value=manifest):
            updates = service.check_updates()

        assert updates == []


# ------------------------------------------------------------------
# TemplateSyncService.pull_updates tests
# ------------------------------------------------------------------


class TestPullUpdates:
    def test_pull_new_template(self, tmp_path):
        repo = TemplateRepository(tmp_path / "templates.db")
        service = TemplateSyncService(repo, remote_url="https://example.com/templates")

        config_data = {"name": "Pulled", "description": "desc", "category": "cat", "format_rules": {}}
        with patch.object(service, "_fetch_template_config", return_value=config_data):
            applied = service.pull_updates([{
                "id": "pulled-tpl",
                "action": "new",
                "version": "1.0",
                "name": "Pulled",
            }])

        assert len(applied) == 1
        record = repo.get("remote-pulled-tpl")
        assert record is not None
        assert record.name == "Pulled"
        assert record.version == "1.0"
        assert record.source == "remote"

    def test_pull_updates_existing_template(self, tmp_path):
        repo = TemplateRepository(tmp_path / "templates.db")
        repo.save_remote_template(
            template_id="old-tpl",
            name="Old Name",
            category="test",
            config={"format_rules": {"body_text": {"font_size": 10}}},
            version="1.0",
        )

        service = TemplateSyncService(repo, remote_url="https://example.com/templates")
        config_data = {"name": "New Name", "description": "", "category": "test", "format_rules": {"body_text": {"font_size": 12}}}
        with patch.object(service, "_fetch_template_config", return_value=config_data):
            applied = service.pull_updates([{
                "id": "old-tpl",
                "action": "update",
                "from_version": "1.0",
                "to_version": "2.0",
                "name": "New Name",
            }])

        assert len(applied) == 1
        record = repo.get("remote-old-tpl")
        assert record is not None
        assert record.name == "New Name"
        assert record.version == "2.0"

    def test_pull_failure_does_not_crash(self, tmp_path):
        repo = TemplateRepository(tmp_path / "templates.db")
        service = TemplateSyncService(repo, remote_url="https://example.com/templates")

        with patch.object(service, "_fetch_template_config", return_value=None):
            applied = service.pull_updates([{
                "id": "fail-tpl",
                "action": "new",
                "version": "1.0",
                "name": "Fail",
            }])

        assert applied == []
        assert repo.get("remote-fail-tpl") is None

    def test_pull_empty_list(self, tmp_path):
        repo = TemplateRepository(tmp_path / "templates.db")
        service = TemplateSyncService(repo, remote_url="https://example.com/templates")
        assert service.pull_updates([]) == []

    def test_pull_calls_check_updates_when_none(self, tmp_path):
        repo = TemplateRepository(tmp_path / "templates.db")
        service = TemplateSyncService(repo, remote_url="https://example.com/templates")
        with patch.object(service, "check_updates", return_value=[]) as mock_check:
            service.pull_updates(None)
        mock_check.assert_called_once()


# ------------------------------------------------------------------
# Sync failure does not affect local usage
# ------------------------------------------------------------------


class TestOfflineFallback:
    def test_local_templates_still_work_after_sync_failure(self, tmp_path):
        repo = TemplateRepository(tmp_path / "templates.db")
        personal = repo.save_personal_template("My Template", "test", {"format_rules": {}})

        service = TemplateSyncService(repo, remote_url="https://example.com/templates")

        # Simulate network failure
        with patch.object(service, "_fetch_manifest", return_value=None):
            updates = service.check_updates()
            assert updates == []

        # Local templates unaffected
        loaded = repo.get(personal.slug)
        assert loaded is not None
        assert loaded.name == "My Template"

    def test_sync_once_handles_exception(self, tmp_path):
        repo = TemplateRepository(tmp_path / "templates.db")
        service = TemplateSyncService(repo, remote_url="https://example.com/templates")

        with patch.object(service, "pull_updates", side_effect=RuntimeError("network")):
            result = service.sync_once()

        assert result == []


# ------------------------------------------------------------------
# Sync logging
# ------------------------------------------------------------------


class TestSyncLogging:
    def test_check_updates_logs_new_templates(self, tmp_path, caplog):
        repo = TemplateRepository(tmp_path / "templates.db")
        service = TemplateSyncService(repo, remote_url="https://example.com/templates")

        manifest = {
            "t1": {"name": "T1", "version": "1.0"},
            "t2": {"name": "T2", "version": "1.0"},
        }
        with patch.object(service, "_fetch_manifest", return_value=manifest):
            with caplog.at_level(logging.INFO):
                service.check_updates()

        assert "2" in caplog.text  # "检查到 2 个模板需要同步"

    def test_pull_updates_logs_success(self, tmp_path, caplog):
        repo = TemplateRepository(tmp_path / "templates.db")
        service = TemplateSyncService(repo, remote_url="https://example.com/templates")

        config_data = {"name": "Logged", "description": "", "category": "cat", "format_rules": {}}
        with patch.object(service, "_fetch_template_config", return_value=config_data):
            with caplog.at_level(logging.INFO):
                service.pull_updates([{
                    "id": "logged-tpl",
                    "action": "new",
                    "version": "1.0",
                    "name": "Logged",
                }])

        assert "成功同步" in caplog.text

    def test_pull_updates_logs_failure(self, tmp_path, caplog):
        repo = TemplateRepository(tmp_path / "templates.db")
        service = TemplateSyncService(repo, remote_url="https://example.com/templates")

        with patch.object(service, "_fetch_template_config", return_value=None):
            with caplog.at_level(logging.WARNING):
                service.pull_updates([{
                    "id": "fail-tpl",
                    "action": "new",
                    "version": "1.0",
                    "name": "Fail",
                }])

        assert "同步模板失败" in caplog.text


# ------------------------------------------------------------------
# auto_sync background thread
# ------------------------------------------------------------------


class TestAutoSync:
    def test_start_and_stop(self, tmp_path):
        repo = TemplateRepository(tmp_path / "templates.db")
        service = TemplateSyncService(repo, remote_url="https://example.com/templates", interval_hours=1)

        with patch.object(service, "sync_once", return_value=[]):
            service.auto_sync()
            assert service._running is True
            assert service._thread is not None
            assert service._thread.is_alive()

            service.stop_sync()
            assert service._running is False

    def test_double_start_is_idempotent(self, tmp_path):
        repo = TemplateRepository(tmp_path / "templates.db")
        service = TemplateSyncService(repo, remote_url="https://example.com/templates", interval_hours=1)

        with patch.object(service, "sync_once", return_value=[]):
            service.auto_sync()
            t1 = service._thread
            service.auto_sync()
            t2 = service._thread
            assert t1 is t2
            service.stop_sync()


# ------------------------------------------------------------------
# seed_builtin_templates with remote_url
# ------------------------------------------------------------------


class TestSeedWithRemote:
    def test_seed_still_works_without_remote(self, tmp_path):
        repo = TemplateRepository(tmp_path / "templates.db")
        templates = repo.list_templates(source="bundled")
        assert len(templates) > 0

    def test_seed_checks_remote_when_url_provided(self, tmp_path, caplog):
        repo = TemplateRepository(tmp_path / "templates.db")

        manifest = {}
        with patch("paper_format_corrector.adapters.storage.template_repository.requests") as mock_requests:
            mock_resp = MagicMock()
            mock_resp.json.return_value = manifest
            mock_resp.raise_for_status = MagicMock()
            mock_requests.get.return_value = mock_resp

            with caplog.at_level(logging.DEBUG):
                repo.seed_builtin_templates(remote_url="https://raw.githubusercontent.com/test/templates/main")

        # Should have attempted the request
        mock_requests.get.assert_called_once()
