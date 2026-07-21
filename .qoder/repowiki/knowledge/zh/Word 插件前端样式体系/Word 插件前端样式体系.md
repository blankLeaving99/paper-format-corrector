---
kind: frontend_style
name: Word 插件前端样式体系
category: frontend_style
scope:
    - '**'
source_files:
    - interfaces/word_addin/src/taskpane.css
    - interfaces/word_addin/src/taskpane.html
---

本仓库的前端样式仅存在于 Word Web Add-in（Office 插件）子模块中，采用最轻量的原生 CSS + HTML + Vanilla JS 方案，未引入任何 CSS 框架、预处理器或构建工具。

**样式系统与方法论**
- 使用 BEM 风格的命名约定：以 `section`、`section-header`、`step-badge`、`btn-primary`、`stat-grid` 等语义化类名组织 UI 块，避免深层嵌套选择器。
- 全局 reset 仅包含 `margin/padding/box-sizing` 基础重置，其余样式全部通过显式类名控制，保证在 Office 宿主环境中的可预测性。
- 颜色与字体通过少量设计常量集中定义：主色 `#1a73e8`（Google Blue）、成功 `#34a853`、错误 `#ea4335`、背景 `#f5f5f5`、卡片白 `#fff`；字体栈 `'Segoe UI', 'Microsoft YaHei', sans-serif`，字号基准 `13px`。
- 交互状态通过 `:hover`、`:disabled`、`.success/.error/.loading` 等修饰类表达，无 JavaScript 动态注入样式。

**关键文件**
- `interfaces/word_addin/src/taskpane.css` — 唯一样式源，256 行纯 CSS，覆盖布局、按钮、进度条、统计网格、状态提示等所有视觉元素。
- `interfaces/word_addin/src/taskpane.html` — 任务窗格模板，内联结构类名与 CSS 一一对应，并通过 `<link>` 引入样式表。
- `interfaces/word_addin/src/taskpane.js` / `office.js` — 行为脚本，不直接操作 style 属性（除 `display:none` 外），遵循结构与表现分离原则。

**架构决策与约束**
- 由于运行在 Office 宿主沙箱中，禁止使用外部 CSS 框架、CDN 资源（除 Microsoft Office JS CDN 的 `office.js` 外）和 CSS-in-JS 方案。
- 样式文件独立于 Python 后端，通过 `manifest.xml` 静态打包分发，无需构建步骤。
- 组件粒度较粗（按“步骤区块”划分），尚未拆分为可复用原子组件，适合当前单一任务窗格的规模。

**开发者规范**
- 新增 UI 元素时沿用现有类名风格（小写连字符、语义化前缀如 `section-*`、`btn-*`、`status.*`）。
- 颜色值优先复用已定义的常量色，避免随意引入新色板。
- 保持响应式友好：容器使用 `max-width: 100%`，统计网格使用 CSS Grid 自适应列数。
- 不在 JS 中硬编码样式字符串，统一通过切换 CSS 类实现状态切换。