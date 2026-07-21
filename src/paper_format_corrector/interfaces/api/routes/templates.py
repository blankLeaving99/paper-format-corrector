"""Template query endpoints.

GET  /api/v1/templates             — list templates with pagination & filters
GET  /api/v1/templates/categories  — list all categories
GET  /api/v1/templates/search      — search by keyword
GET  /api/v1/templates/{id}        — get full template config
"""

from __future__ import annotations

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
