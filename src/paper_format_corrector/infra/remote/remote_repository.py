"""SQLAlchemy-based repository for remote template storage."""

from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .remote_models import Base, RemoteTemplate, RemoteTemplateShare, User


class RemoteTemplateRepository:
    """CRUD operations for the remote template database."""

    def __init__(self, database_url: str | None = None):
        if database_url is None:
            db_path = Path("data") / "remote_templates.db"
            db_path.parent.mkdir(parents=True, exist_ok=True)
            database_url = f"sqlite:///{db_path}"
        self._engine = create_engine(database_url, echo=False)
        Base.metadata.create_all(self._engine)
        self._session_factory = sessionmaker(bind=self._engine)

    def _session(self) -> Session:
        return self._session_factory()

    # ── User operations ────────────────────────────────────────────

    def save_user(self, id: str, username: str, password_hash: str, email: str = "") -> User:
        """Create or update a user."""
        with self._session() as session:
            existing = session.query(User).filter_by(id=id).first()
            if existing:
                existing.username = username
                existing.password_hash = password_hash
                existing.email = email
                session.commit()
                return existing
            user = User(id=id, username=username, password_hash=password_hash, email=email)
            session.add(user)
            session.commit()
            session.refresh(user)
            return user

    def get_user_by_username(self, username: str) -> User | None:
        with self._session() as session:
            return session.query(User).filter_by(username=username).first()

    def get_user_by_id(self, user_id: str) -> User | None:
        with self._session() as session:
            return session.query(User).filter_by(id=user_id).first()

    # ── RemoteTemplate operations ──────────────────────────────────

    def save(self, template: RemoteTemplate) -> str:
        """Save a remote template. If id is None, generate a new UUID. Returns the template id."""
        with self._session() as session:
            if template.id is None:
                template.id = str(uuid.uuid4())
            existing = session.query(RemoteTemplate).filter_by(id=template.id).first()
            if existing:
                existing.name = template.name
                existing.category = template.category
                existing.organization = template.organization
                existing.version = template.version
                existing.config = template.config
                existing.author_id = template.author_id
                existing.is_public = template.is_public
                existing.updated_at = datetime.now()
                session.commit()
                return existing.id
            template.updated_at = datetime.now()
            session.add(template)
            session.commit()
            session.refresh(template)
            return template.id

    def get(self, template_id: str) -> RemoteTemplate | None:
        with self._session() as session:
            return session.query(RemoteTemplate).filter_by(id=template_id).first()

    def delete(self, template_id: str) -> bool:
        with self._session() as session:
            template = session.query(RemoteTemplate).filter_by(id=template_id).first()
            if template is None:
                return False
            session.query(RemoteTemplateShare).filter_by(template_id=template_id).delete()
            session.delete(template)
            session.commit()
            return True

    def search(self, keyword: str, public_only: bool = False) -> list[RemoteTemplate]:
        """Search templates by keyword (name, category, organization)."""
        with self._session() as session:
            query = session.query(RemoteTemplate)
            if public_only:
                query = query.filter_by(is_public="true")
            like = f"%{keyword}%"
            query = query.filter(
                (RemoteTemplate.name.like(like))
                | (RemoteTemplate.category.like(like))
                | (RemoteTemplate.organization.like(like))
            )
            return query.order_by(RemoteTemplate.updated_at.desc()).all()

    def list_public(self) -> list[RemoteTemplate]:
        with self._session() as session:
            return session.query(RemoteTemplate).filter_by(is_public="true").order_by(RemoteTemplate.updated_at.desc()).all()

    def list_by_author(self, author_id: str) -> list[RemoteTemplate]:
        with self._session() as session:
            return session.query(RemoteTemplate).filter_by(author_id=author_id).order_by(RemoteTemplate.updated_at.desc()).all()

    # ── Share operations ───────────────────────────────────────────

    def add_share(self, template_id: str, shared_with_user_id: str, permission_level: str = "read") -> str:
        """Create a share record. Returns the share id."""
        share_id = str(uuid.uuid4())
        with self._session() as session:
            share = RemoteTemplateShare(
                id=share_id,
                template_id=template_id,
                shared_with_user_id=shared_with_user_id,
                permission_level=permission_level,
            )
            session.add(share)
            session.commit()
            return share_id

    def get_shares(self, template_id: str) -> list[RemoteTemplateShare]:
        with self._session() as session:
            return session.query(RemoteTemplateShare).filter_by(template_id=template_id).all()

    def get_shared_with_user(self, user_id: str) -> list[RemoteTemplateShare]:
        with self._session() as session:
            return session.query(RemoteTemplateShare).filter_by(shared_with_user_id=user_id).all()

    def has_write_access(self, template_id: str, user_id: str) -> bool:
        """Check if a user has write access to a template."""
        with self._session() as session:
            template = session.query(RemoteTemplate).filter_by(id=template_id).first()
            if template and template.author_id == user_id:
                return True
            share = (
                session.query(RemoteTemplateShare)
                .filter_by(template_id=template_id, shared_with_user_id=user_id, permission_level="write")
                .first()
            )
            return share is not None

    def has_read_access(self, template_id: str, user_id: str) -> bool:
        """Check if a user can read a template (public, owner, or has share)."""
        with self._session() as session:
            template = session.query(RemoteTemplate).filter_by(id=template_id).first()
            if template is None:
                return False
            if template.is_public == "true":
                return True
            if template.author_id == user_id:
                return True
            share = (
                session.query(RemoteTemplateShare)
                .filter_by(template_id=template_id, shared_with_user_id=user_id)
                .first()
            )
            return share is not None
