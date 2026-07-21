---
kind: external_dependency
name: FastAPI - REST API 框架
slug: fastapi
category: external_dependency
category_hints:
    - vendor_identity
scope:
    - '**'
---

### FastAPI
- **角色**: Web API 服务框架，提供 HTTP 端点供外部调用
- **集成点**: `src/paper_format_corrector/api/app.py` 中创建 FastAPI 实例并定义路由
- **使用模式**: 提供 /correct、/scan、/plan、/learn 等端点，支持文件上传和批量处理
- **文档**: 自动生成 OpenAPI 文档在 /docs 路径