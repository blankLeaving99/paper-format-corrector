---
kind: external_dependency
name: pdfplumber - PDF 文本提取库
slug: pdfplumber
category: external_dependency
category_hints:
    - vendor_identity
scope:
    - '**'
---

### pdfplumber
- **角色**: PDF 反向学习功能的核心依赖
- **集成点**: `src/paper_format_corrector/infrastructure/parsers/pdf_style_extractor.py` 中从 PDF 提取格式信息
- **使用模式**: 从原生 PDF 中提取文本块、字体信息、布局数据，生成与现有风格工作流兼容的配置