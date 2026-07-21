"""Template query endpoints.

GET  /api/v1/templates                — list templates with pagination & filters
GET  /api/v1/templates/categories     — list all categories
GET  /api/v1/templates/search         — search by keyword
GET  /api/v1/templates/{id}           — get full template config
GET  /api/v1/templates/sync/list      — list public templates for remote sync
GET  /api/v1/templates/sync/{id}      — get a single remote template by ID
POST /api/v1/templates/sync/push      — push a new template to the remote
POST /api/v1/templates/sync/{id}      — update an existing remote template
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from paper_format_corrector.infra.template_repository import TemplateRepository

router = APIRouter(tags=["templates"])


def _repo() -> TemplateRepository:
    return TemplateRepository()


def _template_summary(t: Any) -> dict[str, Any]:
    return {
        "slug": t.slug,
        "name": t.name,
        "category": t.category,
        "source": t.source,
        "organization": t.organization,
        "version": t.version,
        "is_active": t.is_active,
        "tags": t.tags,
    }


# ── List templates ─────────────────────────────────────────────


@router.get(
    "/api/v1/templates",
    summary="模板列表",
    description="获取模板列表，支持按分类、来源、关键词过滤，以及分页。",
    response_model=dict[str, Any],
    responses={
        200: {
            "description": "模板列表",
            "content": {
                "application/json": {
                    "example": {
                        "items": [
                            {
                                "slug": "ieee",
                                "name": "IEEE 期刊论文",
                                "category": "journal",
                                "source": "builtin",
                                "organization": "IEEE",
                                "version": "1.0",
                                "is_active": True,
                                "tags": ["英文", "期刊"],
                            }
                        ],
                        "total": 1,
                        "page": 1,
                        "per_page": 20,
                    }
                }
            },
        }
    },
)
def list_templates(
    category: str | None = Query(None, description="按分类过滤"),
    source: str | None = Query(None, description="按来源过滤 (builtin / personal)"),
    keyword: str | None = Query(None, description="按关键词搜索模板名称"),
    page: int = Query(1, ge=1, description="页码"),
    per_page: int = Query(20, ge=1, le=100, description="每页数量"),
) -> dict[str, Any]:
    repo = _repo()

    if keyword:
        templates = repo.search_templates(keyword)
    else:
        templates = repo.list_templates(category=category)

    if source:
        templates = [t for t in templates if t.source == source]

    total = len(templates)
    start = (page - 1) * per_page
    end = start + per_page
    page_items = templates[start:end]

    return {
        "items": [_template_summary(t) for t in page_items],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


# ── Categories ─────────────────────────────────────────────────


@router.get(
    "/api/v1/templates/categories",
    summary="模板分类列表",
    description="返回所有模板分类及其包含的模板数量。",
    responses={
        200: {
            "description": "分类列表",
            "content": {
                "application/json": {
                    "example": [
                        {"category": "journal", "count": 5},
                        {"category": "thesis", "count": 12},
                    ]
                }
            },
        }
    },
)
def list_categories() -> list[dict[str, Any]]:
    repo = _repo()
    return repo.list_categories()


# ── Search ─────────────────────────────────────────────────────


@router.get(
    "/api/v1/templates/search",
    summary="搜索模板",
    description="按关键词模糊搜索模板名称、描述和标签。",
    responses={
        200: {
            "description": "搜索结果",
            "content": {
                "application/json": {
                    "example": {
                        "query": "清华",
                        "items": [
                            {
                                "slug": "tsinghua-thesis",
                                "name": "清华大学学位论文",
                                "category": "thesis",
                            }
                        ],
                        "total": 1,
                    }
                }
            },
        }
    },
)
def search_templates(
    q: str = Query(..., min_length=1, description="搜索关键词"),
) -> dict[str, Any]:
    repo = _repo()
    results = repo.search_templates(q)
    return {
        "query": q,
        "items": [_template_summary(t) for t in results],
        "total": len(results),
    }


# ── Get single template ────────────────────────────────────────


@router.get(
    "/api/v1/templates/{template_id}",
    summary="模板详情",
    description="获取指定模板的完整配置，包括格式规则、分类、版本等元信息。",
    responses={
        200: {
            "description": "模板完整信息",
            "content": {
                "application/json": {
                    "example": {
                        "slug": "ieee",
                        "name": "IEEE 期刊论文",
                        "category": "journal",
                        "source": "builtin",
                        "config": {"format_rules": {"margins": {"top": 2.54}}},
                    }
                }
            },
        },
        404: {"description": "模板不存在"},
    },
)
def get_template(template_id: str) -> dict[str, Any]:
    repo = _repo()
    record = repo.get(template_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"模板不存在: {template_id}")

    return {
        "slug": record.slug,
        "name": record.name,
        "category": record.category,
        "source": record.source,
        "organization": record.organization,
        "degree_level": record.degree_level,
        "discipline": record.discipline,
        "language": record.language,
        "version": record.version,
        "tags": record.tags,
        "description": record.description,
        "config": record.config,
        "is_active": record.is_active,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }


# ── Sync endpoints (for remote template server) ──────────────────


@router.get(
    "/api/v1/templates/sync/list",
    summary="同步模板列表",
    description="返回所有公共模板列表，供远程客户端拉取同步使用。",
    response_model=list[dict[str, Any]],
)
def sync_list_templates() -> list[dict[str, Any]]:
    """List all public templates for remote synchronization."""
    repo = _repo()
    templates = repo.list_templates(active_only=True)
    return [_sync_template_summary(t) for t in templates if t.source == "bundled" or t.remote_id]


@router.get(
    "/api/v1/templates/sync/{remote_id}",
    summary="获取远程模板详情",
    description="按 remote_id 获取模板完整配置，供远程客户端拉取。",
    responses={200: {"description": "模板详情"}, 404: {"description": "模板不存在"}},
)
def sync_get_template(remote_id: str) -> dict[str, Any]:
    """Get a single template by remote_id for synchronization."""
    repo = _repo()
    record = repo.find_by_remote_id(remote_id)
    if record is None:
        # Fallback: try slug lookup for backward compatibility
        record = repo.get(remote_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"远程模板不存在: {remote_id}")
    return _sync_template_full(record)


@router.post(
    "/api/v1/templates/sync/push",
    summary="推送新模板",
    description="将本地模板推送到远程服务器。如果未提供 id，则创建新模板并分配 remote_id。",
    response_model=dict[str, Any],
)
def sync_push_template(payload: dict[str, Any]) -> dict[str, Any]:
    """Push a new template to the remote repository.

    Request body:
        name (str): Template name
        category (str): Template category
        config (dict): Format rules configuration
        organization (str, optional): Organization name
        version (str, optional): Version string
        description (str, optional): Description
        tags (list[str], optional): Tags
        is_public (str, optional): Visibility ('true'/'false'/'share_link')
    """
    name = payload.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="模板名称不能为空")

    category = payload.get("category", "同步模板")
    config = payload.get("config", {})
    description = payload.get("description", "")
    organization = payload.get("organization", "")
    tags = payload.get("tags", [])

    remote_id = str(uuid.uuid4())
    repo = _repo()
    saved = repo.save_personal_template(
        name=name,
        category=category,
        config=config,
        description=description,
        tags=tags,
        organization=organization,
    )
    repo.set_remote_id(saved.slug, remote_id)
    repo.update_template(saved.slug, {"source_url": f"remote:{remote_id}"})

    return {
        "id": remote_id,
        "slug": saved.slug,
        "name": saved.name,
        "category": saved.category,
        "created_at": datetime.now().isoformat(),
    }


@router.post(
    "/api/v1/templates/sync/{remote_id}",
    summary="更新远程模板",
    description="按 remote_id 更新已有模板的配置和元信息。",
    response_model=dict[str, Any],
)
def sync_update_template(remote_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Update an existing remote template by remote_id."""
    repo = _repo()
    record = repo.find_by_remote_id(remote_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"远程模板不存在: {remote_id}")

    updates: dict[str, Any] = {}
    for field in ("name", "category", "organization", "version", "description"):
        if field in payload:
            updates[field] = payload[field]
    if "config" in payload:
        updates["config"] = payload["config"]
    if "tags" in payload:
        updates["tags"] = payload["tags"]

    if updates:
        repo.update_template(record.slug, updates)

    return {
        "id": remote_id,
        "slug": record.slug,
        "name": payload.get("name", record.name),
        "updated_at": datetime.now().isoformat(),
    }


def _sync_template_summary(t: Any) -> dict[str, Any]:
    return {
        "id": t.remote_id or t.slug,
        "slug": t.slug,
        "name": t.name,
        "category": t.category,
        "source": t.source,
        "organization": t.organization,
        "version": t.version,
        "config": t.config,
        "tags": t.tags,
        "is_public": "true",
        "updated_at": t.updated_at,
    }


def _sync_template_full(record: Any) -> dict[str, Any]:
    return {
        "id": record.remote_id or record.slug,
        "slug": record.slug,
        "name": record.name,
        "category": record.category,
        "organization": record.organization,
        "version": record.version,
        "config": record.config,
        "description": record.description,
        "tags": record.tags,
        "is_public": "true",
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }
