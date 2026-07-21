"""Collaboration service bridging local and remote template repositories."""

from __future__ import annotations

import uuid
from datetime import datetime

from ..template_repository import TemplateRecord, TemplateRepository
from .remote_models import RemoteTemplate
from .remote_repository import RemoteTemplateRepository


class CollaborationService:
    """Orchestrates template sync between local SQLite and remote database."""

    def __init__(self, local_repo: TemplateRepository, remote_repo: RemoteTemplateRepository):
        self.local = local_repo
        self.remote = remote_repo

    def sync_to_remote(self, template_id: str, user_id: str) -> str:
        """Upload a local template to the remote repository. Returns the remote template ID."""
        template = self.local.get(template_id)
        if template is None:
            raise ValueError(f"本地模板不存在: {template_id}")

        remote_template = RemoteTemplate(
            id=str(uuid.uuid4()),
            name=template.name,
            category=template.category,
            organization=template.organization,
            version=template.version,
            config=template.config,
            author_id=user_id,
            is_public="true",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        remote_id = self.remote.save(remote_template)

        self.local.set_remote_id(template_id, remote_id)
        return remote_id

    def sync_from_remote(self, remote_id: str, user_id: str) -> TemplateRecord:
        """Download a remote template to the local repository.

        Raises:
            ValueError: If the remote template doesn't exist or access is denied.
        """
        remote_template = self.remote.get(remote_id)
        if remote_template is None:
            raise ValueError(f"远程模板不存在: {remote_id}")
        if not self.remote.has_read_access(remote_id, user_id):
            raise ValueError("无权限访问该模板")

        tags = []
        if remote_template.config:
            tags = remote_template.config.get("_tags", [])

        record = self.local.save_personal_template(
            name=remote_template.name,
            category=remote_template.category or "远程模板",
            config=remote_template.config or {},
            description=f"来自远程模板库: {remote_template.name}",
            tags=tags,
            organization=remote_template.organization,
            language=remote_template.config.get("_language", "中文") if remote_template.config else "中文",
        )
        self.local.set_remote_id(record.slug, remote_id)
        return record

    def share_template(self, template_id: str, user_id: str, shared_with_user_id: str, permission: str = "read") -> str:
        """Share a remote template with another user. Returns the share ID.

        The user must own the template or have admin access.
        """
        remote_template = self.remote.get(template_id)
        if remote_template is None:
            raise ValueError(f"远程模板不存在: {template_id}")
        if remote_template.author_id != user_id:
            raise ValueError("只有模板作者才能分享模板")
        if permission not in ("read", "write"):
            raise ValueError(f"无效的权限级别: {permission}")

        return self.remote.add_share(template_id, shared_with_user_id, permission)

    def search_public_templates(self, keyword: str = "") -> list[RemoteTemplate]:
        """Search public templates in the remote repository."""
        if keyword:
            return self.remote.search(keyword, public_only=True)
        return self.remote.list_public()

    def get_template_permissions(self, template_id: str) -> dict:
        """Get the permission summary for a remote template."""
        remote_template = self.remote.get(template_id)
        if remote_template is None:
            raise ValueError(f"远程模板不存在: {template_id}")
        shares = self.remote.get_shares(template_id)
        return {
            "template_id": template_id,
            "is_public": remote_template.is_public,
            "author_id": remote_template.author_id,
            "shares": [
                {"user_id": s.shared_with_user_id, "permission": s.permission_level}
                for s in shares
            ],
        }
