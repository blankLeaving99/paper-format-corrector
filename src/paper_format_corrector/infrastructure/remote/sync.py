"""Synchronization service for local ↔ remote template repositories."""

from __future__ import annotations

from ..template_repository import TemplateRepository
from .conflict_resolver import ConflictResolver
from .remote_repository import RemoteTemplateRepository


class SyncService:
    """Manages bidirectional sync between local and remote template repositories."""

    def __init__(self, local_repo: TemplateRepository, remote_repo: RemoteTemplateRepository):
        self.local = local_repo
        self.remote = remote_repo
        self._resolver = ConflictResolver()

    def pull_all(self, user_id: str) -> list[str]:
        """Pull all public templates from remote to local.

        Returns:
            List of template names that were newly added.
        """
        public_templates = self.remote.list_public()
        added: list[str] = []
        for t in public_templates:
            existing = self.local.find_by_remote_id(t.id)
            if existing is None:
                tags = []
                if t.config:
                    tags = t.config.get("_tags", [])
                record = self.local.save_personal_template(
                    name=t.name,
                    category=t.category or "远程模板",
                    config=t.config or {},
                    description=f"来自远程模板库: {t.name}",
                    tags=tags,
                    organization=t.organization,
                )
                self.local.set_remote_id(record.slug, t.id)
                added.append(t.name)
        return added

    def push_all(self, user_id: str) -> list[str]:
        """Push all personal templates that have no remote_id to the remote.

        Returns:
            List of template names that were pushed.
        """
        from ..template_repository import TemplateRecord
        all_templates = self.local.list_templates(source="personal", active_only=True)
        pushed: list[str] = []
        for t in all_templates:
            remote_id = self.local.get_remote_id(t.slug)
            if not remote_id:
                from .remote_models import RemoteTemplate
                remote_template = RemoteTemplate(
                    name=t.name,
                    category=t.category,
                    organization=t.organization,
                    version=t.version,
                    config=t.config,
                    author_id=user_id,
                )
                new_remote_id = self.remote.save(remote_template)
                self.local.set_remote_id(t.slug, new_remote_id)
                pushed.append(t.name)
        return pushed

    def pull_updates(self, template_id: str) -> dict:
        """Check remote for updates to a local template and merge if needed.

        Returns:
            dict with keys:
              - status: 'up_to_date' | 'updated' | 'conflicts'
              - conflicts: list of conflicting field keys (if any)
              - merged_config: the merged config dict (if updated)
        """
        remote_id = self.local.get_remote_id(template_id)
        if not remote_id:
            return {"status": "no_remote_id", "conflicts": [], "merged_config": None}

        local_template = self.local.get(template_id)
        remote_template = self.remote.get(remote_id)

        if local_template is None:
            return {"status": "local_not_found", "conflicts": [], "merged_config": None}
        if remote_template is None:
            return {"status": "remote_not_found", "conflicts": [], "merged_config": None}

        local_updated = local_template.updated_at or ""
        remote_updated = str(remote_template.updated_at or "")

        if remote_updated <= local_updated:
            return {"status": "up_to_date", "conflicts": [], "merged_config": None}

        merged = self._resolver.resolve(local_template.config, remote_template.config or {})
        conflicts = self._resolver.list_conflicts(merged)

        if conflicts:
            return {"status": "conflicts", "conflicts": conflicts, "merged_config": merged}

        self.local.update_template(template_id, {"config": merged})
        return {"status": "updated", "conflicts": [], "merged_config": merged}

    def get_sync_status(self, user_id: str) -> dict:
        """Get a summary of sync status for the user."""
        local_personal = self.local.list_templates(source="personal", active_only=True)
        remote_public = self.remote.list_public()
        remote_by_user = self.remote.list_by_author(user_id)

        local_with_remote = 0
        local_without_remote = 0
        for t in local_personal:
            if self.local.get_remote_id(t.slug):
                local_with_remote += 1
            else:
                local_without_remote += 1

        return {
            "local_personal_count": len(local_personal),
            "local_synced_count": local_with_remote,
            "local_unsynced_count": local_without_remote,
            "remote_public_count": len(remote_public),
            "remote_my_count": len(remote_by_user),
        }
