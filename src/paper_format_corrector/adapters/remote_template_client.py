"""HTTP client for remote template synchronization.

Provides push/pull operations against a remote template server.
Falls back to local-only mode when the network is unavailable.
"""

from __future__ import annotations

import json
import logging
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from .storage.template_repository import TemplateRecord

logger = logging.getLogger(__name__)

# Timeout for HTTP requests in seconds
_DEFAULT_TIMEOUT = 10


class RemoteTemplateClient:
    """HTTP client that talks to the remote template API.

    Features:
    - Local-first: checks local cache before hitting the network.
    - Offline degradation: returns cached/stale data when unreachable.
    - Conflict resolution: based on ``updated_at`` timestamp (latest wins).

    Usage::

        client = RemoteTemplateClient("http://template-server:8000")
        client.pull_all(local_repo)
        client.push_template(local_repo, "personal-my-template")
    """

    def __init__(self, base_url: str, timeout: float = _DEFAULT_TIMEOUT):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    # ── Low-level HTTP ────────────────────────────────────────────

    def _get(self, path: str) -> dict | list | None:
        """GET request. Returns parsed JSON or None on failure."""
        url = f"{self.base_url}{path}"
        try:
            req = Request(url, method="GET", headers={"Accept": "application/json"})
            with urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (URLError, OSError, json.JSONDecodeError) as exc:
            logger.warning("Remote GET %s failed: %s", path, exc)
            return None

    def _post(self, path: str, payload: dict) -> dict | None:
        """POST request with JSON body. Returns parsed JSON or None."""
        url = f"{self.base_url}{path}"
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        try:
            req = Request(
                url,
                data=data,
                method="POST",
                headers={"Content-Type": "application/json", "Accept": "application/json"},
            )
            with urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (URLError, OSError, json.JSONDecodeError) as exc:
            logger.warning("Remote POST %s failed: %s", path, exc)
            return None

    def _delete(self, path: str) -> dict | None:
        """DELETE request. Returns parsed JSON or None."""
        url = f"{self.base_url}{path}"
        try:
            req = Request(url, method="DELETE", headers={"Accept": "application/json"})
            with urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (URLError, OSError, json.JSONDecodeError) as exc:
            logger.warning("Remote DELETE %s failed: %s", path, exc)
            return None

    # ── Pull operations ───────────────────────────────────────────

    def pull_list(self) -> list[dict]:
        """Fetch the list of remote templates.

        Returns:
            List of template dicts from the server, or empty list on failure.
        """
        result = self._get("/api/v1/templates/sync/list")
        if result is None:
            return []
        if isinstance(result, dict) and "items" in result:
            return result["items"]
        if isinstance(result, list):
            return result
        return []

    def pull_template(self, remote_id: str) -> dict | None:
        """Fetch a single remote template by ID.

        Returns:
            Template dict or None on failure.
        """
        return self._get(f"/api/v1/templates/sync/{remote_id}")

    def pull_all(self, local_repo: Any, user_id: str = "") -> list[str]:
        """Pull all public templates from remote into the local repository.

        For each remote template:
        - If a local template with the same ``remote_id`` exists and remote is newer,
          merge using timestamp-based conflict resolution.
        - If no local match, create a new personal template.

        Args:
            local_repo: A ``TemplateRepository`` instance.
            user_id: Optional user identifier for ownership tracking.

        Returns:
            List of template names that were newly added or updated.
        """
        remote_templates = self.pull_list()
        touched: list[str] = []
        for remote_t in remote_templates:
            remote_id = remote_t.get("id", "")
            if not remote_id:
                continue
            local_existing = local_repo.find_by_remote_id(remote_id)
            if local_existing:
                # Conflict resolution: remote wins if its updated_at is newer
                remote_updated = remote_t.get("updated_at", "")
                local_updated = local_existing.updated_at or ""
                if remote_updated > local_updated:
                    merged_config = self._resolve_conflict(
                        local_existing.config, remote_t.get("config", {}), local_updated, remote_updated
                    )
                    local_repo.update_template(local_existing.slug, {"config": merged_config})
                    touched.append(local_existing.name)
            else:
                tags = remote_t.get("tags", [])
                if not tags and isinstance(remote_t.get("config"), dict):
                    tags = remote_t["config"].get("_tags", [])
                record = local_repo.save_personal_template(
                    name=remote_t.get("name", "Unnamed"),
                    category=remote_t.get("category", "远程模板"),
                    config=remote_t.get("config", {}),
                    description=remote_t.get("description", ""),
                    tags=tags,
                    organization=remote_t.get("organization", ""),
                )
                local_repo.set_remote_id(record.slug, remote_id)
                touched.append(record.name)
        return touched

    # ── Push operations ───────────────────────────────────────────

    def push_template(self, local_repo: Any, slug: str) -> str | None:
        """Push a local template to the remote server.

        If the local template already has a ``remote_id``, update the remote.
        Otherwise create a new remote template.

        Returns:
            The remote template ID, or None on failure.
        """
        record = local_repo.get(slug)
        if record is None:
            logger.warning("Local template %s not found, skipping push", slug)
            return None

        remote_id = local_repo.get_remote_id(slug)
        payload = self._template_to_payload(record, remote_id)

        if remote_id:
            result = self._post(f"/api/v1/templates/sync/{remote_id}", payload)
        else:
            result = self._post("/api/v1/templates/sync/push", payload)

        if result and result.get("id"):
            new_remote_id = result["id"]
            local_repo.set_remote_id(slug, new_remote_id)
            return new_remote_id
        return None

    def push_all(self, local_repo: Any, user_id: str = "") -> list[str]:
        """Push all personal templates that lack a remote_id to the remote.

        Returns:
            List of template names that were pushed.
        """
        personal = local_repo.list_templates(source="personal", active_only=True)
        pushed: list[str] = []
        for t in personal:
            if not local_repo.get_remote_id(t.slug):
                remote_id = self.push_template(local_repo, t.slug)
                if remote_id:
                    pushed.append(t.name)
        return pushed

    # ── Conflict resolution ───────────────────────────────────────

    @staticmethod
    def _resolve_conflict(
        local_config: dict,
        remote_config: dict,
        local_updated: str,
        remote_updated: str,
    ) -> dict:
        """Resolve conflict between local and remote configs.

        Strategy: latest ``updated_at`` wins. For fields that differ,
        the remote version takes precedence when remote is newer.
        """
        if remote_updated >= local_updated:
            return remote_config
        return local_config

    # ── Helpers ───────────────────────────────────────────────────

    @staticmethod
    def _template_to_payload(record: TemplateRecord, remote_id: str | None = None) -> dict:
        """Convert a TemplateRecord to a JSON-safe dict for the API."""
        payload: dict[str, Any] = {
            "name": record.name,
            "category": record.category,
            "organization": record.organization,
            "version": record.version,
            "config": record.config,
            "description": record.description,
            "tags": record.tags,
            "is_public": "true",
        }
        if remote_id:
            payload["id"] = remote_id
        return payload

    def is_online(self) -> bool:
        """Check if the remote server is reachable."""
        result = self._get("/health")
        return result is not None and result.get("status") == "ok"
