---
kind: external_dependency
name: python-docx - Word 文档处理库
slug: python-docx
category: external_dependency
category_hints:
    - vendor_identity
scope:
    - '**'
---

### python-docx
- **角色**: 核心依赖，用于读写 .docx 格式的学术论文文档
- **集成点**: `src/paper_format_corrector/infrastructure/converters/file_formatter.py` 中通过 `from docx import Document` 导入
- **使用模式**: 作为格式矫正引擎的基础，负责加载模板、解析段落样式、应用字体和页面设置
- **注意**: 这是项目最核心的外部依赖，所有文档操作都基于此库