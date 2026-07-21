# API 使用指南

论文格式自动矫正工具 v3.0 — REST API 完整使用指南

---

## 目录

- [1. 启动 API 服务](#1-启动-api-服务)
- [2. 调用示例](#2-调用示例)
- [3. 所有端点详细说明](#3-所有端点详细说明)
- [4. 错误码解释](#4-错误码解释)
- [5. 限流和使用建议](#5-限流和使用建议)

---

## 1. 启动 API 服务

### 1.1 直接启动

```bash
python -m paper_format_corrector.api.app
```

默认监听 `0.0.0.0:8000`。

### 1.2 使用 uvicorn 启动（推荐生产环境）

```bash
# 安装 uvicorn
pip install uvicorn

# 启动服务
uvicorn paper_format_corrector.api.app:app --host 0.0.0.0 --port 8000

# 开发模式（自动重载）
uvicorn paper_format_corrector.api.app:app --reload --host 127.0.0.1 --port 8000
```

### 1.3 验证服务

```bash
curl http://localhost:8000/health
# 返回: {"status":"ok","service":"paper-format-correction"}
```

### 1.4 API 文档

启动后访问自动生成的交互式文档：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## 2. 调用示例

### 2.1 curl 示例

**矫正论文**

```bash
curl -X POST http://localhost:8000/correct \
  -F "file=@paper.docx" \
  -F "preset=ieee" \
  --output corrected.docx
```

**扫描文档结构**

```bash
curl -X POST http://localhost:8000/scan \
  -F "file=@paper.docx"
```

**生成矫正计划（dry-run）**

```bash
curl -X POST http://localhost:8000/plan \
  -F "file=@paper.docx" \
  -F "preset=apa"
```

**从样本学习格式**

```bash
curl -X POST http://localhost:8000/learn \
  -F "file=@sample.docx"
```

**批量矫正**

```bash
curl -X POST http://localhost:8000/batch \
  -F "files=@paper1.docx" \
  -F "files=@paper2.docx" \
  -F "files=@paper3.docx" \
  -F "preset=ieee" \
  --output batch_results.zip
```

**列出模板**

```bash
curl http://localhost:8000/templates
curl http://localhost:8000/templates?category=journal
curl http://localhost:8000/templates?keyword=ieee
```

**获取模板详情**

```bash
curl http://localhost:8000/templates/ieee
```

**创建模板**

```bash
curl -X POST http://localhost:8000/templates \
  -H "Content-Type: application/json" \
  -d '{
    "name": "我的模板",
    "category": "personal",
    "config": {
      "format_rules": {
        "font": {"chinese": "宋体", "english": "Times New Roman"},
        "body_text": {"font_size": 12, "line_spacing": 1.5, "align": "justify"},
        "margins": {"top": 2.54, "bottom": 2.54, "left": 3.17, "right": 3.17}
      }
    }
  }'
```

**导出模板**

```bash
curl http://localhost:8000/templates/ieee/export?format=yaml --output ieee_template.yaml
curl http://localhost:8000/templates/ieee/export?format=json --output ieee_template.json
```

**删除模板**

```bash
curl -X DELETE http://localhost:8000/templates/my_template
```

**验证模板配置**

```bash
curl -X POST http://localhost:8000/templates/validate \
  -H "Content-Type: application/json" \
  -d @my_template.json
```

**列出预设**

```bash
curl http://localhost:8000/presets
```

**查看报告**

```bash
curl http://localhost:8000/reports
curl http://localhost:8000/reports/1
```

### 2.2 Python 示例

**使用 requests 库**

```python
import requests

BASE_URL = "http://localhost:8000"

# 矫正论文
with open("paper.docx", "rb") as f:
    response = requests.post(
        f"{BASE_URL}/correct",
        files={"file": ("paper.docx", f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        data={"preset": "ieee"},
    )

with open("corrected.docx", "wb") as f:
    f.write(response.content)

# 扫描文档
with open("paper.docx", "rb") as f:
    response = requests.post(
        f"{BASE_URL}/scan",
        files={"file": ("paper.docx", f)},
    )
result = response.json()
print(f"元素统计: {result['elements']}")
print(f"页边距: {result['margins']}")

# 列出模板
templates = requests.get(f"{BASE_URL}/templates").json()
for t in templates:
    print(f"{t['slug']}: {t['name']} ({t['category']})")
```

**使用内置 Python 客户端**

```python
from paper_format_corrector.api.client import PaperFormatClient

client = PaperFormatClient(base_url="http://localhost:8000")

# 矫正论文
result = client.correct_document("paper.docx", preset="ieee")
with open("corrected.docx", "wb") as f:
    f.write(result)

# 批量矫正
result = client.batch_correct(["paper1.docx", "paper2.docx"], preset="ieee")
with open("batch_results.zip", "wb") as f:
    f.write(result)

# 扫描文档
scan_result = client.scan_document("paper.docx")
print(scan_result)

# 学习样本
learn_result = client.learn_style("sample.docx")
print(learn_result)

# 列出模板
templates = client.list_templates()
for t in templates:
    print(t)

# 创建模板
client.create_template("我的模板", "personal", {
    "format_rules": {
        "font": {"chinese": "宋体", "english": "Times New Roman"},
        "body_text": {"font_size": 12, "line_spacing": 1.5},
    }
})
```

### 2.3 JavaScript 示例

**使用 fetch API**

```javascript
const BASE_URL = "http://localhost:8000";

// 矫正论文
async function correctPaper(file, preset) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("preset", preset);

  const response = await fetch(`${BASE_URL}/correct`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`矫正失败: ${response.statusText}`);
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `corrected_${file.name}`;
  a.click();
  URL.revokeObjectURL(url);
}

// 扫描文档
async function scanDocument(file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${BASE_URL}/scan`, {
    method: "POST",
    body: formData,
  });

  return await response.json();
}

// 列出模板
async function listTemplates(category) {
  const url = category
    ? `${BASE_URL}/templates?category=${category}`
    : `${BASE_URL}/templates`;

  const response = await fetch(url);
  return await response.json();
}
```

---

## 3. 所有端点详细说明

### 3.1 健康检查

| 项目 | 说明 |
|------|------|
| 方法 | `GET` |
| 路径 | `/health` |
| 认证 | 无 |
| 参数 | 无 |

**响应**

```json
{
  "status": "ok",
  "service": "paper-format-correction"
}
```

---

### 3.2 文档矫正

| 项目 | 说明 |
|------|------|
| 方法 | `POST` |
| 路径 | `/correct` |
| 认证 | 无 |
| Content-Type | `multipart/form-data` |

**请求参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `file` | File | 是 | `.docx` 文件 |
| `preset` | string | 否 | 预设名称（如 `ieee`、`apa`） |

**响应**

- 成功：返回矫正后的 `.docx` 文件（二进制流）
- Header `X-Correction-Report` 包含矫正报告 JSON

**错误**

- `400` — 文件格式不支持（非 `.docx`）
- `500` — 矫正失败

---

### 3.3 扫描文档结构

| 项目 | 说明 |
|------|------|
| 方法 | `POST` |
| 路径 | `/scan` |
| Content-Type | `multipart/form-data` |

**请求参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `file` | File | 是 | `.docx` 文件 |

**响应**

```json
{
  "elements": {
    "title": 1,
    "heading1": 5,
    "heading2": 12,
    "heading3": 8,
    "body": 45,
    "figure_caption": 3,
    "table_caption": 2,
    "reference": 20
  },
  "margins": {
    "top": 2.54,
    "bottom": 2.54,
    "left": 3.17,
    "right": 3.17
  },
  "confidence": [
    {"paragraph": 0, "type": "title", "confidence": 0.95},
    {"paragraph": 1, "type": "heading1", "confidence": 0.88}
  ],
  "page_setup": {
    "width": 21.0,
    "height": 29.7
  }
}
```

---

### 3.4 生成矫正计划

| 项目 | 说明 |
|------|------|
| 方法 | `POST` |
| 路径 | `/plan` |
| Content-Type | `multipart/form-data` |

**请求参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `file` | File | 是 | `.docx` 文件 |
| `preset` | string | 否 | 预设名称 |

**响应**

```json
{
  "total_affected": 15,
  "items": [
    {
      "paragraph_index": 2,
      "type": "heading1",
      "description": "字体从 宋体 改为 黑体",
      "confidence": 0.92
    }
  ],
  "risk_items": [
    {
      "paragraph_index": 10,
      "type": "body",
      "description": "低置信度识别，建议人工确认"
    }
  ]
}
```

---

### 3.5 从样本学习

| 项目 | 说明 |
|------|------|
| 方法 | `POST` |
| 路径 | `/learn` |
| Content-Type | `multipart/form-data` |

**请求参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `file` | File | 是 | 排版正确的样本文档 |

**响应**

```json
{
  "profile": {
    "body_font_size": 12,
    "body_line_spacing": 1.5,
    "heading1_font_size": 16,
    "margins": {"top": 2.54, "bottom": 2.54, "left": 3.17, "right": 3.17}
  },
  "explanation": "检测到正文 12pt、1.5 倍行距、首行缩进 2 字符..."
}
```

---

### 3.6 批量矫正

| 项目 | 说明 |
|------|------|
| 方法 | `POST` |
| 路径 | `/batch` |
| Content-Type | `multipart/form-data` |

**请求参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `files` | File[] | 是 | 多个 `.docx` 文件 |
| `preset` | string | 否 | 预设名称 |

**响应**

- 返回 ZIP 压缩包，包含：
  - 所有矫正后的 `.docx` 文件
  - `batch_summary.txt` — 文本格式汇总
  - `batch_summary.md` — Markdown 格式汇总

---

### 3.7 模板管理

#### 列出模板

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/templates` | 列出所有模板 |

**查询参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `category` | string | 否 | 按分类筛选 |
| `keyword` | string | 否 | 关键词搜索 |

#### 获取模板详情

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/templates/{slug}` | 获取模板完整配置 |

#### 创建模板

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/templates` | 创建个人模板 |

**请求体**

```json
{
  "name": "模板名称",
  "category": "personal",
  "config": {
    "format_rules": { ... }
  }
}
```

#### 删除模板

| 方法 | 路径 | 说明 |
|------|------|------|
| `DELETE` | `/templates/{slug}` | 删除模板（内置模板仅禁用） |

#### 导出模板

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/templates/{slug}/export` | 导出模板文件 |

**查询参数**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `format` | string | `yaml` | 导出格式：`yaml` 或 `json` |

#### 获取模板摘要

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/templates/{slug}/summary` | 获取模板样式摘要 |

#### 列出分类

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/templates/categories/list` | 列出所有分类及数量 |

#### 列出组织

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/templates/organizations/list` | 列出所有组织及数量 |

#### 列出标签

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/templates/tags/list` | 列出所有标签及使用次数 |

#### 验证模板

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/templates/validate` | 验证模板配置 |

**请求体**：JSON 格式的模板配置

**响应**

```json
{
  "is_valid": true,
  "errors": [],
  "warnings": [],
  "missing_fields": [],
  "suggestions": []
}
```

---

### 3.8 高校模板导入

#### 启动导入

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/university-import/start` | 启动高校模板导入工作流 |

**查询参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `university` | string | 是 | 高校名称 |
| `requirement_file` | string | 是 | 需求文档路径 |

#### 查询状态

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/university-import/status` | 查询导入工作流状态 |

---

### 3.9 预设列表

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/presets` | 列出所有内置预设 |

---

### 3.10 报告管理

#### 列出报告

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/reports` | 列出历史处理报告 |

**查询参数**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `limit` | int | 50 | 返回数量上限 |

#### 获取报告详情

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/reports/{record_id}` | 获取单条报告详情 |

---

## 4. 错误码解释

### 4.1 HTTP 状态码

| 状态码 | 含义 | 常见原因 |
|--------|------|----------|
| `200` | 成功 | 请求正常处理 |
| `400` | 请求错误 | 文件格式不支持、缺少必填参数 |
| `404` | 未找到 | 模板/报告不存在 |
| `500` | 服务器错误 | 矫正过程中发生异常 |

### 4.2 错误响应格式

```json
{
  "detail": "错误描述信息"
}
```

### 4.3 常见错误

| 错误信息 | 原因 | 解决方案 |
|----------|------|----------|
| `仅支持 .docx 格式文件` | 上传了非 .docx 文件 | 转换为 .docx 后重试 |
| `矫正失败，未生成输出文件` | 矫正过程异常 | 检查文件是否损坏，查看服务端日志 |
| `矫正失败: xxx` | 具体矫正错误 | 根据错误信息排查 |
| `模板不存在: xxx` | 模板 slug 不存在 | 先调用 `/templates` 列出可用模板 |
| `没有有效的 .docx 文件` | 批量上传中无有效文件 | 确保文件扩展名为 .docx |
| `请上传至少一个文件` | 批量上传为空 | 上传至少一个文件 |

---

## 5. 限流和使用建议

### 5.1 限流策略

当前版本没有内置限流机制，但建议：

- **并发控制**：单次请求处理一个文档，避免同时发送大量请求
- **批量处理**：使用 `/batch` 端点处理多文件，而非并行调用 `/correct`
- **超时设置**：客户端应设置合理的超时（建议 60-120 秒）

### 5.2 性能建议

| 场景 | 建议 |
|------|------|
| 小文件（< 1MB） | 直接调用 `/correct` |
| 大文件（> 5MB） | 增加客户端超时到 120 秒 |
| 批量处理 | 使用 `/batch`，一次上传所有文件 |
| 需要预览 | 先调用 `/plan` 再调用 `/correct` |
| 需要评分 | 客户端本地调用 `QualityScorer` |

### 5.3 安全建议

- API 默认监听 `0.0.0.0`，生产环境建议：
  - 限制为内网访问
  - 添加认证中间件
  - 使用反向代理（Nginx/Caddy）
  - 启用 HTTPS

### 5.4 客户端最佳实践

```python
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 创建带重试的 session
session = requests.Session()
retries = Retry(total=3, backoff_factor=1)
session.mount("http://", HTTPAdapter(max_retries=retries))

# 设置超时
response = session.post(
    "http://localhost:8000/correct",
    files={"file": open("paper.docx", "rb")},
    timeout=120,
)
```

### 5.5 部署建议

```bash
# 生产环境使用多 worker
uvicorn paper_format_corrector.api.app:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --log-level info
```
