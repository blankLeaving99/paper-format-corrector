---
kind: external_dependency
name: Pandoc - 文档转换工具
slug: pandoc
category: external_dependency
category_hints:
    - vendor_identity
scope:
    - '**'
---

### Pandoc
- **角色**: DOCX 到 LaTeX 的高质量转换工具
- **集成点**: `src/paper_format_corrector/infrastructure/converters/latex_exporter.py` 中优先使用 pandoc 进行转换
- **使用模式**: 检测系统中 pandoc 可执行文件，支持 Windows、macOS、Linux 常见安装路径
- **降级策略**: 如果 pandoc 不可用，则回退到纯文本提取 + LaTeX 模板包装
- **特点**: 支持多种文档类（article、report、book、ctexart 等）和中文字体支持