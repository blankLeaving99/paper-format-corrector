"""FastAPI application entry point with Swagger/ReDoc configuration.

Usage:
    python -m paper_format_corrector.interfaces.api.app
    # or
    uvicorn paper_format_corrector.interfaces.api.app:app --host 0.0.0.0 --port 8000

Docs:
    /docs   — Swagger UI
    /redoc  — ReDoc
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from paper_format_corrector import __version__
from .routes import batch, correct, health, reports, scan, templates

app = FastAPI(
    title="论文格式矫正 API",
    description=(
        "Paper Format Correction Service\n\n"
        "自动矫正论文格式的 REST API，支持模板查询、文档扫描、异步文档矫正。\n\n"
        "## 功能模块\n"
        "- **健康检查** — 服务状态与依赖检测\n"
        "- **模板管理** — 查询、搜索、分类浏览模板库\n"
        "- **文档矫正** — 上传文档异步矫正并下载结果\n"
        "- **文档扫描** — 分析文档结构与格式\n"
        "- **批量处理** — 多文件批量矫正并打包下载\n"
        "- **处理报告** — 查询历史处理记录和详情"
    ),
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    openapi_tags=[
        {
            "name": "health",
            "description": "服务健康检查与依赖状态",
        },
        {
            "name": "templates",
            "description": "模板查询、搜索与分类浏览",
        },
        {
            "name": "correct",
            "description": "文档格式矫正（异步任务）",
        },
        {
            "name": "scan",
            "description": "文档结构扫描与分析",
        },
        {
            "name": "batch",
            "description": "多文件批量矫正",
        },
        {
            "name": "reports",
            "description": "处理历史与报告查询",
        },
    ],
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(health.router)
app.include_router(templates.router)
app.include_router(correct.router)
app.include_router(scan.router)
app.include_router(batch.router)
app.include_router(reports.router)


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {
        "service": "paper-format-correction",
        "version": __version__,
        "docs": "/docs",
        "redoc": "/redoc",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
