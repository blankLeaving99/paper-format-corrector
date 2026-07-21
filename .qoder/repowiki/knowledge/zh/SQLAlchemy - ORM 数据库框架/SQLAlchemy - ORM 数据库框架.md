---
kind: external_dependency
name: SQLAlchemy - ORM 数据库框架
slug: sqlalchemy
category: external_dependency
category_hints:
    - vendor_identity
scope:
    - '**'
---

### SQLAlchemy
- **角色**: 远程模板库的数据库 ORM 层
- **集成点**: `src/paper_format_corrector/infra/remote/remote_repository.py` 中管理用户、模板和权限数据
- **使用模式**: SQLite 后端存储协作模板库数据，支持用户认证、模板分享和权限控制
- **默认存储**: data/remote_templates.db