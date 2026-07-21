---
kind: external_dependency
name: Tesseract OCR - 光学字符识别
slug: tesseract-ocr
category: external_dependency
category_hints:
    - vendor_identity
scope:
    - '**'
---

### Tesseract OCR
- **角色**: 扫描版 PDF 的 OCR 回退方案
- **集成点**: `src/paper_format_corrector/infrastructure/parsers/pdf_style_extractor.py` 中处理图像型 PDF
- **使用模式**: 结合 pdf2image 将 PDF 页面转换为图像，然后使用 pytesseract 进行文字识别
- **依赖链**: pytesseract + pdf2image + Tesseract 可执行文件
- **可选依赖**: 需要额外安装系统级 Tesseract OCR 引擎