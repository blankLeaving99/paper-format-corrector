# T3: 协作模板库 - 实现计划

## Context

当前项目只有本地 SQLite 模板库（`infra/template_repository.py`，使用原生 sqlite3），无远程数据库、无用户认证、无协作功能。本任务在 `infra/remote/` 下新建协作模块，实现远程模板存储、用户认证、模板同步与冲突合并。

## 约束

- Python 3.9+（使用 `from __future__ import annotations`）
- 遵循项目现有风格：ruff 120 字符行宽、pytest tmp_path fixtures、frozen dataclass 等
- 新增依赖：sqlalchemy、bcrypt、pyjwt（添加到 pyproject.toml optional-dependencies）
- 遵循安全约定：密码必须哈希、JWT secret 从环境变量读取、token 有过期时间
- `infra/remote/` 为新建目录，需创建 `__init__.py`

## 文件变更

### 1. 新建 `src/paper_format_corrector/infra/remote/__init__.py`
- 导出主要公共类

### 2. 新建 `src/paper_format_corrector/infra/remote/remote_models.py`
- SQLAlchemy declarative_base 模型
- `RemoteTemplate` 表：id, name, category, organization, version, config(JSON), author_id(FK→User), created_at, updated_at, is_public('true'/'false'/'share_link')
- `User` 表：id, username(unique), password_hash, email, created_at
- `RemoteTemplateShare` 表：id, template_id(FK), shared_with_user_id(FK), permission_level('read'/'write')
- `RemoteTemplate` 上建立 `author` relationship

### 3. 新建 `src/paper_format_corrector/infra/remote/auth.py`
- `AuthService` 类，使用 bcrypt 哈希密码，PyJWT 签发/验证 token
- `register(username, password, email)` → 创建用户，返回 user_id
- `login(username, password)` → 验证密码，返回 JWT token（含 user_id, username, exp）
- `verify_token(token)` → 返回 payload dict（含 user_id, username），失败抛 ValueError
- SECRET_KEY 从 `os.environ.get("TEMPLATE_REPO_SECRET_KEY", "dev-secret-key")` 读取
- token 默认过期时间 7 天

### 4. 新建 `src/paper_format_corrector/infra/remote/remote_repository.py`
- `RemoteTemplateRepository` 类，封装 SQLAlchemy 操作
- `__init__(database_url)` → 创建 engine + sessionmaker，默认 `sqlite:///data/remote_templates.db`
- `save(template)` → upsert（按 id）
- `get(template_id)` → 返回 RemoteTemplate 或 None
- `delete(template_id)` → 删除
- `search(keyword, public_only=False)` → 按 name/category/organization 模糊搜索
- `list_public()` → 返回所有 is_public='true' 的模板
- `list_by_author(author_id)` → 返回某用户的所有模板
- `save_user(user)` / `get_user_by_username(username)` / `get_user_by_id(user_id)`

### 5. 新建 `src/paper_format_corrector/infra/remote/collaboration.py`
- `CollaborationService(local_repo, remote_repo)` 组合本地 TemplateRepository 和 RemoteTemplateRepository
- `sync_to_remote(template_id, user_id)` → 从本地取模板，转为 RemoteTemplate，存到远程
- `sync_from_remote(remote_id, user_id)` → 从远程取模板，校验权限（public 或 author_id==user_id），存到本地
- `share_template(template_id, user_id, shared_with_user_id, permission)` → 创建 Share 记录
- `search_public_templates(keyword)` → 搜索公共模板

### 6. 新建 `src/paper_format_corrector/infra/remote/conflict_resolver.py`
- `ConflictResolver` 类
- `resolve(local: dict, remote: dict, base: dict | None = None)` → 3 路合并
  - 无 base 时：按 updated_at 优先；相同 key 不同 value 标记 conflict
  - 有 base 时：标准 3-way merge（base vs local, base vs remote，无冲突取 non-base 值）
- `has_conflicts(merged: dict) -> bool` → 检查合并结果中是否有 conflict 标记
- `list_conflicts(merged: dict) -> list[str]` → 返回有冲突的 key 列表

### 7. 新建 `src/paper_format_corrector/infra/remote/sync.py`
- `SyncService(local_repo, remote_repo)`
- `pull_all(user_id)` → 拉取所有公共模板到本地（跳过已存在的）
- `push_all(user_id)` → 推送所有个人模板到远程（无 remote_id 的）
- `pull_updates(template_id)` → 检查远程更新并合并，返回 status + conflicts
- `get_sync_status(user_id)` → 返回同步状态摘要

### 8. 修改 `src/paper_format_corrector/infra/template_repository.py`
- 在 `TemplateRecord` 中添加 `remote_id: str = ""` 字段
- 在 `save_personal_template` 和 `_record_with_meta` 中处理 remote_id
- 添加 `find_by_remote_id(remote_id)` 方法
- 添加 `set_remote_id(slug, remote_id)` 方法

### 9. 修改 `pyproject.toml`
- 在 `[project.optional-dependencies]` 添加：
  ```
  remote = ["sqlalchemy>=2.0,<3.0", "bcrypt>=4.0,<5.0", "pyjwt>=2.8,<3.0"]
  ```

### 10. 新建 `tests/test_collaboration.py`
- 测试 AuthService：注册、登录、token 验证、重复注册、错误密码
- 测试 RemoteTemplateRepository：CRUD、搜索、权限
- 测试 CollaborationService：上传、下载、分享、权限控制
- 测试 ConflictResolver：无冲突合并、远程优先、本地优先、字段级冲突
- 测试 SyncService：pull_all、push_all、pull_updates
- 所有测试使用 tmp_path 和内存数据库

## 验证

1. 运行 `ruff check src/paper_format_corrector/infra/remote/ tests/test_collaboration.py`
2. 运行 `python -m pytest tests/test_collaboration.py -v`
3. 运行 `python -m pytest tests/test_template_repository.py -v`（确保无回归）
