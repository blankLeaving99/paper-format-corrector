---
kind: external_dependency
name: Microsoft Office JavaScript API - Word 插件开发
slug: office-js-api
category: external_dependency
category_hints:
    - vendor_identity
scope:
    - '**'
---

### Microsoft Office JavaScript API
- **角色**: Word 插件的前端开发框架
- **集成点**: `interfaces/word_addin/src/office.js` 和 `functions.html` 中使用 Office.js 与 Word 文档交互
- **使用模式**: 实现 Word 插件功能，包括模板选择、格式矫正、结果预览等
- **部署**: 通过 manifest.xml 注册为 Word 插件，支持在线和本地部署