---
kind: external_dependency
name: PyMuPDF - PDF 处理库
slug: pymupdf
category: external_dependency
category_hints:
    - vendor_identity
scope:
    - '**'
---

### PyMuPDF (fitz)
- **角色**: PDF 处理的备选后端
- **集成点**: `src/paper_format_corrector/infrastructure/parsers/pdf_style_extractor.py` 中作为 pdfplumber 的替代方案
- **使用模式**: 当 pdfplumber 不可用时自动降级到 PyMuPDF，同样支持文本块和字体元数据提取
- **特点**: 性能通常优于 pdfplumber，但安装可能更复杂