# 任务分解计划

基于 plan(1).md 验收标准，按模块拆解为可独立执行的子任务。

---

## 已完成

### T1 启动器自动化 ✅
- [x] `run.py` 检测已有 `.venv`，用 `os.execv()` 自动切入
- [x] 创建 venv 后安装全部依赖（必需+可选），自动重启
- [x] `_find_venv_python()` 启动前执行 `--version` 验证解释器合法性
- [x] `compat.py` 新增 `get_required_packages()` / `get_optional_packages()` / `get_all_packages()`

### T2 模板兜底 ✅
- [x] `FormatCorrector.__init__` 模板文件不存在时 fallback 到空白 `Document()`
- [x] `app.py` 模板路径读取改为 `config.get("template", {}).get("path", "")`
- [x] `extract_template_info()` 模板不存在时打印提示并 return

### T3 GUI 模板上传 ✅
- [x] `gui.py` 新增 `template_input` 文件上传控件 + 传递给 `process_paper()`
- [x] `desktop_gui.py` 新增 `template_path_var` + `DropFileEntry` 拖拽输入框
- [x] 两个 GUI 上传后覆盖 config 中默认模板路径

### T4 安全加固 ✅
- [x] `preset_loader.py` 预设名正则校验 + 路径穿越检测
- [x] `llm_parser.py` SSRF 防护（空 host 拒绝、HTTPS 强制、域名白名单）
- [x] `file_converter.py` + `format_exporter.py` LibreOffice 查找优先绝对路径
- [x] `gui.py` atexit 清理临时目录、`max_file_size="50mb"`
- [x] `desktop_gui.py` 拖拽拒绝 UNC 路径 + 扩展名校验、异常信息脱敏
- [x] `app.py` 配置验证（margins 必须为数字）

### T5 基础测试 ✅
- [x] `tests/test_startup_and_template.py` 覆盖：compat 导出、模板 fallback、app 配置处理、venv 检测、可选依赖

### T6 CLAUDE.md ✅
- [x] 项目概览、命令、架构、安全约定、预设说明

---

## 待完成

### T7 打包与分发
**目标**: exe 打包时包含默认模板和必要资源，路径解析正确
- [ ] `build.py` 打包脚本检查：模板文件、config、presets 是否包含在 bundle 中
- [ ] `run.py` frozen 模式下资源路径解析验证（`sys.frozen` + `sys._MEIPASS`）
- [ ] 打包后 `.venv` 不存在时的首次安装流程测试
- **验收**: 双击 exe → 自动装依赖 → 选择 GUI → 正常处理文档

### T8 需求文档模板集成
**目标**: 需求文档解析结果中如包含模板路径，应正确覆盖
- [ ] `app.py:apply_requirement()` 解析结果中检查 `template.path` 字段
- [ ] 若需求文档指定了模板路径，覆盖 `self.template_path` 并重建 corrector
- [ ] 测试：需求文档中写 `模板：xxx.docx` → 矫正器使用该模板
- **验收**: 需求文档可指定模板，优先级：需求文档模板 > config 模板 > 空白兜底

### T9 CLI 模板交互增强
**目标**: CLI 不传 `-t` 且默认模板缺失时，提示用户但不阻塞
- [ ] `cli.py` 处理单文件时，模板不存在只 warning 不 error
- [ ] 增加 `--no-template` 参数显式跳过模板
- **验收**: `python -m paper_format_corrector -f paper.docx` 无模板也能跑

### T10 Gradio GUI 健壮性
**目标**: Web GUI 异常不崩溃，用户看到友好提示
- [ ] `gui.py:process_paper()` 全流程 try-except，异常返回到 UI 而非 500
- [ ] 上传非 docx 模板文件时的错误提示
- [ ] 大文件处理超时提示
- **验收**: 上传损坏文件 → UI 显示错误信息 → 不影响后续使用

### T11 桌面 GUI 健壮性
**目标**: tkinter GUI 线程安全，异常不冻结窗口
- [ ] `_run_correct` / `_run_batch_correct` 线程内异常正确回传到 UI
- [ ] 处理过程中禁用"开始矫正"按钮，防止重复提交
- [ ] 批量处理增加进度条或计数器
- **验收**: 处理失败 → 结果区显示错误 → 按钮恢复可用

### T12 补充测试
**目标**: 覆盖核心流程的关键路径
- [ ] `test_startup_and_template.py` 增加：预设名路径穿越拒绝测试
- [ ] `test_startup_and_template.py` 增加：config margins 类型错误拒绝测试
- [ ] `test_corrector.py` 增加：无模板时矫正流程测试
- [ ] `test_presets.py` 增加：非法预设名（含 `../`）应抛 ValueError
- **验收**: `pytest tests/ -v` 全通过，新增测试覆盖安全相关边界

### T13 README 更新
**目标**: 反映最新的启动流程和模板机制
- [ ] 更新"快速开始"章节：说明 run.py 自动切 venv 的行为
- [ ] 更新"目录结构"章节：新增 `.claude/`、`CLAUDE.md`
- [ ] 更新"安装"章节：说明可选依赖自动安装
- **验收**: 新用户按 README 操作可一步到位

---

## 依赖关系

```
T7 (打包) ← T2 (模板兜底) ← 已完成
T8 (需求模板) ← T3 (GUI上传) ← 已完成
T9 (CLI增强) ← T2 ← 已完成
T10 (Web GUI健壮) ← T3 ← 已完成
T11 (桌面GUI健壮) ← T3 ← 已完成
T12 (补充测试) ← T4 (安全加固) ← 已完成
T13 (README) ← T1+T2+T3 ← 已完成
```

T7~T13 互不阻塞，可并行执行。

---

## 执行建议

| 优先级 | 任务 | 理由 |
|--------|------|------|
| P0 | T12 | 补测试，防止后续改动回归 |
| P1 | T8, T9 | 完善模板流程闭环 |
| P1 | T10, T11 | GUI 健壮性直接影响用户体验 |
| P2 | T7 | 打包分发，影响 exe 用户 |
| P2 | T13 | 文档，影响新用户上手 |
