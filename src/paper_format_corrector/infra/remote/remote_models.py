"""SQLAlchemy models for remote template storage and user management."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, JSON, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class User(Base):
    """User account for authentication."""

    __tablename__ = "users"

    id = Column(String, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    email = Column(String, default="")
    created_at = Column(DateTime, default=datetime.now)

    templates = relationship("RemoteTemplate", back_populates="author", lazy="dynamic")


class RemoteTemplate(Base):
    """Template stored in the remote repository."""

    __tablename__ = "remote_templates"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    category = Column(String, default="")
    organization = Column(String, default="")
    version = Column(String, default="1.0")
    config = Column(JSON, default=dict)
    author_id = Column(String, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    is_public = Column(String, default="true")  # true / false / share_link

    author = relationship("User", back_populates="templates")
    shares = relationship("RemoteTemplateShare", back_populates="template", lazy="dynamic")


class RemoteTemplateShare(Base):
    """Share permission for a template with a specific user."""

    __tablename__ = "remote_template_shares"

    id = Column(String, primary_key=True)
    template_id = Column(String, ForeignKey("remote_templates.id"), nullable=False)
    shared_with_user_id = Column(String, ForeignKey("users.id"), nullable=False)
    permission_level = Column(String, default="read")  # read / write
    created_at = Column(DateTime, default=datetime.now)

    template = relationship("RemoteTemplate", back_populates="shares")
    shared_with_user = relationship("User")
