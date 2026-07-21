"""Health check endpoint.

GET /api/v1/health — returns service status, version, and dependency checks.
"""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter

from paper_format_corrector import __version__

router = APIRouter(tags=["health"])


def _check_template_library() -> str:
    """Check if template library (SQLite) is accessible."""
    try:
        from paper_format_corrector.adapters.storage.template_repository import TemplateRepository
        repo = TemplateRepository()
        templates = repo.list_templates()
        return "ok"
    except Exception:
        return "unavailable"


def _check_dependencies() -> dict[str, str]:
    """Check if core dependencies are importable."""
    deps: dict[str, str] = {}
    for module, label in [
        ("docx", "python-docx"),
        ("yaml", "pyyaml"),
        ("lxml", "lxml"),
        ("PIL", "Pillow"),
    ]:
        try:
            __import__(module)
            deps[label] = "ok"
        except ImportError:
            deps[label] = "missing"
    return deps


@router.get(
    "/api/v1/health",
    summary="健康检查",
    description="返回服务运行状态、版本号、模板库连接状态及核心依赖可用性。",
    response_model=dict[str, Any],
    responses={
        200: {
            "description": "服务正常运行",
            "content": {
                "application/json": {
                    "example": {
                        "status": "ok",
                        "version": "3.0.0",
                        "timestamp": "2026-07-21T10:00:00",
                        "checks": {
                            "template_library": "ok",
                            "dependencies": {
                                "python-docx": "ok",
                                "pyyaml": "ok",
                                "lxml": "ok",
                                "Pillow": "ok",
                            },
                        },
                    }
                }
            },
        }
    },
)
def health_check() -> dict[str, Any]:
    return {
        "status": "ok",
        "version": __version__,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "checks": {
            "template_library": _check_template_library(),
            "dependencies": _check_dependencies(),
        },
    }
