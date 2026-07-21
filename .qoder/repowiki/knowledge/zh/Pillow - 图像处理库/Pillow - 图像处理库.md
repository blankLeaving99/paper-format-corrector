---
kind: external_dependency
name: Pillow - 图像处理库
slug: pillow
category: external_dependency
category_hints:
    - vendor_identity
scope:
    - '**'
---

### Pillow
- **角色**: 图片处理和 DPI 检查
- **集成点**: `src/paper_format_corrector/infrastructure/handlers/image_handler.py` 中处理论文中的图片
- **使用模式**: 检查图片分辨率、调整大小、验证格式兼容性
- **版本约束**: >=9.0