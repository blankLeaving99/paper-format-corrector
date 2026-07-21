---
kind: external_dependency
name: PyYAML - YAML 配置文件解析
slug: pyyaml
category: external_dependency
category_hints:
    - vendor_identity
scope:
    - '**'
---

### PyYAML
- **角色**: 解析预设模板和配置文件
- **集成点**: `src/paper_format_corrector/infra/preset_loader.py` 中加载 presets/ 目录下的 YAML 模板文件
- **使用模式**: 38 种内置格式预设（IEEE、Nature、Science、APA、中国高校等）均以 YAML 格式存储
- **版本约束**: >=6.0,<7.0