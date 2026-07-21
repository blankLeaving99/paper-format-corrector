"""论文格式矫正工具 - CLI 入口

支持两种使用方式:
  1. 子命令模式 (推荐):
     python -m paper_format_corrector scan -f paper.docx
     python -m paper_format_corrector correct -f paper.docx --preset ieee
     python -m paper_format_corrector template list
  2. 向后兼容的平铺参数模式:
     python -m paper_format_corrector -f paper.docx --preset ieee
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ...app import PaperFormatCorrector
from ...core.correction.doc_generator import DocGenerator
from ...adapters.word.file_formatter import FormatCorrector
from ...adapters.storage.doc_template_loader import list_doc_templates, load_doc_template
from ...adapters.preset_loader import format_preset_list, get_preset_choices

# ======================================================================
# 子命令: scan
# ======================================================================

def cmd_scan(args: argparse.Namespace) -> None:
    """扫描文档结构和样式"""
    from .services.style_workbench import build_correction_plan, scan_document

    path = Path(args.file)
    if not path.is_file():
        print(f"错误: 文件不存在: {args.file}")
        sys.exit(1)

    print(f"\n扫描文档: {path.name}")
    print("=" * 60)

    inventory = scan_document(path)
    elements = inventory["elements"]

    print(f"\n总段落数: {elements.get('total_paragraphs', 0)}")
    print(f"\n{'元素类型':<12} {'数量':>6}  {'说明'}")
    print("-" * 50)

    element_labels = {
        "body": "正文段落",
        "heading1": "一级标题",
        "heading2": "二级标题",
        "heading3": "三级标题",
        "table": "表格",
        "image": "图片",
        "code": "代码块",
        "formula": "公式",
        "reference": "参考文献",
        "abstract": "摘要",
    }
    for key, label in element_labels.items():
        count = elements.get(key, 0)
        if count > 0:
            print(f"  {label:<12} {count:>6}")

    if inventory.get("margins"):
        m = inventory["margins"]
        print(f"\n页边距: 上={m.get('top', '?')}cm  下={m.get('bottom', '?')}cm  "
              f"左={m.get('left', '?')}cm  右={m.get('right', '?')}cm")

    if inventory.get("page_setup"):
        ps = inventory["page_setup"]
        print(f"页面尺寸: {ps.get('page_width_cm', '?')}cm x {ps.get('page_height_cm', '?')}cm")

    if inventory.get("confidence"):
        print(f"\n{'置信度报告':}")
        print(f"  {'元素':<12} {'级别':<6} {'原因'}")
        print("  " + "-" * 46)
        for item in inventory["confidence"]:
            level_map = {"high": "高", "medium": "中", "low": "低"}
            level = level_map.get(item.get("confidence", ""), item.get("confidence", ""))
            print(f"  {item.get('element', ''):<12} {level:<6} {item.get('reason', '')}")

    if inventory.get("samples"):
        print("\n文本样例 (每类最多5条):")
        for ptype, samples in inventory["samples"].items():
            print(f"\n  [{ptype}]")
            for s in samples[:3]:
                text = s.get("text", "")[:60]
                print(f"    #{s.get('position', '?')}: {text}")

    if inventory.get("issues"):
        print(f"\n发现 {len(inventory['issues'])} 个格式问题:")
        for issue in inventory["issues"][:10]:
            print(f"  - {issue}")

    # 如果指定了配置，生成修正计划
    if args.config:
        print("\n生成修正计划...")
        plan = build_correction_plan(path, args.config.get("format_rules", {}))
        print(f"\n修正计划 (影响 {plan.total_affected} 个元素):")
        for item in plan.items:
            print(f"  {item.element_type}: {item.element_count} 个 -> {item.action} (来源: {item.source})")
        if plan.risk_items:
            print("\n风险项:")
            for risk in plan.risk_items:
                print(f"  - {risk.get('type', '')}: {risk.get('detail', '')}")

    print("\n扫描完成。")


# ======================================================================
# 子命令: learn
# ======================================================================

def cmd_learn(args: argparse.Namespace) -> None:
    """从样本文档学习格式"""
    from .services.style_workbench import explain_style_profile, learn_style_profile

    path = Path(args.file)
    if not path.is_file():
        print(f"错误: 文件不存在: {args.file}")
        sys.exit(1)

    print(f"\n从样本文档学习: {path.name}")
    print("=" * 60)

    explanation = explain_style_profile(path)
    rules = learn_style_profile(path)

    print(f"\n学习置信度: {explanation.get('confidence', '未知')}")
    print(f"扫描段落数: {explanation.get('elements_scanned', 0)}")
    print(f"注意事项: {explanation.get('notice', '')}")

    if explanation.get("learned"):
        print("\n学习到的规则:")
        print(f"  {'元素':<10} {'规则'}")
        print("  " + "-" * 50)
        for item in explanation["learned"]:
            rule_str = json.dumps(item.get("rule", {}), ensure_ascii=False)[:60]
            print(f"  {item.get('element', ''):<10} {rule_str}")

    if explanation.get("margins"):
        print("\n页边距:")
        for k, v in explanation["margins"].items():
            print(f"  {k}: {v}")

    if explanation.get("source_issues"):
        print("\n样本文档问题:")
        for issue in explanation["source_issues"][:5]:
            print(f"  - {issue}")

    # 保存规则到文件
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(rules, f, ensure_ascii=False, indent=2)
        print(f"\n规则已保存到: {output_path}")
    else:
        print("\n规则 JSON:")
        print(json.dumps(rules, ensure_ascii=False, indent=2))


# ======================================================================
# 子命令: template
# ======================================================================

def cmd_template(args: argparse.Namespace) -> None:
    """模板管理子命令"""
    from .adapters.storage.template_repository import TemplateRepository

    repo = TemplateRepository()
    sub = args.template_action

    if sub == "list":
        _template_list(repo, args)
    elif sub == "import":
        _template_import(repo, args)
    elif sub == "export":
        _template_export(repo, args)
    elif sub == "delete":
        _template_delete(repo, args)
    elif sub == "info":
        _template_info(repo, args)
    elif sub == "update":
        _template_update(repo, args)
    else:
        print(f"未知的模板操作: {sub}")
        sys.exit(1)


def _template_list(repo, args):
    """列出模板"""
    category = getattr(args, "category", None)
    search = getattr(args, "search", None)

    if search:
        templates = repo.search_templates(search)
    else:
        templates = repo.list_templates(category=category, active_only=not getattr(args, "all", False))

    if not templates:
        print("未找到模板。")
        return

    print(f"\n共 {len(templates)} 个模板:")
    print(f"{'Slug':<30} {'名称':<20} {'分类':<15} {'来源':<10} {'版本':<6}")
    print("-" * 85)

    for t in templates:
        source_map = {"bundled": "内置", "personal": "个人", "official": "官方", "imported": "导入"}
        source_label = source_map.get(t.source, t.source)
        print(f"  {t.slug:<28} {t.name:<18} {t.category:<13} {source_label:<8} {t.version:<6}")


def _template_import(repo, args):
    """导入模板"""
    file_path = Path(args.file)
    if not file_path.is_file():
        print(f"错误: 文件不存在: {args.file}")
        sys.exit(1)

    try:
        if file_path.suffix.lower() == ".yaml":
            record = repo.import_from_yaml(file_path)
        elif file_path.suffix.lower() == ".json":
            record = repo.import_from_json(file_path)
        else:
            print(f"错误: 不支持的文件格式: {file_path.suffix} (支持 .yaml / .json)")
            sys.exit(1)
        print("模板导入成功:")
        print(f"  名称: {record.name}")
        print(f"  Slug: {record.slug}")
        print(f"  分类: {record.category}")
    except Exception as e:
        print(f"导入失败: {e}")
        sys.exit(1)


def _template_export(repo, args):
    """导出模板"""
    slug = args.slug
    record = repo.get(slug)
    if record is None:
        print(f"错误: 模板不存在: {slug}")
        sys.exit(1)

    output = Path(args.output) if args.output else Path(f"{slug}.yaml")
    fmt = args.format if hasattr(args, "format") and args.format else "yaml"

    try:
        if fmt == "json":
            repo.export_to_json(slug, output)
        else:
            repo.export_to_yaml(slug, output)
        print(f"模板已导出: {output}")
    except Exception as e:
        print(f"导出失败: {e}")
        sys.exit(1)


def _template_delete(repo, args):
    """删除模板"""
    slug = args.slug
    record = repo.get(slug)
    if record is None:
        print(f"错误: 模板不存在: {slug}")
        sys.exit(1)

    if record.source == "bundled":
        print(f"内置模板 '{record.name}' 不能直接删除，已设为禁用。")
        repo.delete_template(slug)
    else:
        confirm = input(f"确定删除模板 '{record.name}' ({slug})? [y/N] ").strip().lower()
        if confirm == "y":
            repo.delete_template(slug)
            print(f"已删除: {record.name}")
        else:
            print("已取消。")


def _template_info(repo, args):
    """查看模板详情"""
    slug = args.slug
    record = repo.get(slug)
    if record is None:
        print(f"错误: 模板不存在: {slug}")
        sys.exit(1)

    source_map = {"bundled": "内置模板", "personal": "个人模板", "official": "官方模板", "imported": "导入模板"}
    print("\n模板详情:")
    print(f"  名称:     {record.name}")
    print(f"  Slug:     {record.slug}")
    print(f"  分类:     {record.category}")
    print(f"  来源:     {source_map.get(record.source, record.source)}")
    print(f"  版本:     {record.version}")
    print(f"  组织:     {record.organization or '未设置'}")
    print(f"  学历:     {record.degree_level or '未设置'}")
    print(f"  学科:     {record.discipline or '未设置'}")
    print(f"  语言:     {record.language}")
    print(f"  启用:     {'是' if record.is_active else '否'}")
    print(f"  创建时间: {record.created_at}")
    print(f"  更新时间: {record.updated_at}")

    if record.tags:
        print(f"  标签:     {', '.join(record.tags)}")

    # 版本历史
    versions = repo.get_versions(slug)
    if versions:
        print(f"\n  版本历史 ({len(versions)} 个版本):")
        for v in versions[:5]:
            print(f"    v{v['version']} ({v['created_at'][:10]}): {v.get('changelog', '无说明')}")


def _template_update(repo, args):
    """检查云端模板更新"""
    import yaml

    # 加载更新配置
    config_path = Path("config/updater.yaml")
    remote_url = getattr(args, "remote_url", None)

    if not remote_url and config_path.exists():
        try:
            with open(config_path, encoding="utf-8") as f:
                updater_config = yaml.safe_load(f) or {}
            remote_url = updater_config.get("updater", {}).get("remote_url", "")
        except Exception:
            pass

    if not remote_url:
        print("错误: 未配置远程仓库地址。请在 config/updater.yaml 中设置 remote_url 或使用 --remote-url 参数。")
        sys.exit(1)

    from .adapters.updater import VersionChecker

    checker = VersionChecker(remote_url)

    # 获取本地模板版本
    local_versions: dict[str, str] = {}
    for t in repo.list_templates(active_only=False):
        # 去掉 slug 前缀得到 template_id
        template_id = t.slug
        for prefix in ("remote-", "personal-", "builtin-"):
            if template_id.startswith(prefix):
                template_id = template_id[len(prefix):]
                break
        local_versions[template_id] = t.version

    print("\n正在检查云端模板更新...")
    print(f"远程仓库: {remote_url}")

    try:
        updates = checker.check_updates(local_versions)
    except Exception as e:
        print(f"\n检查更新失败（网络不可用或仓库地址错误）: {e}")
        print("已降级为跳过更新检查，不影响本地模板使用。")
        return

    if not updates:
        print("\n所有模板已是最新。")
        return

    print(f"\n发现 {len(updates)} 个更新:")
    for u in updates:
        if u["action"] == "new":
            print(f"  + {u['name']} (新模板 v{u['version']})")
        else:
            print(f"  ~ {u['name']} {u['from_version']} -> {u['to_version']}")

    # 询问是否应用
    apply = getattr(args, "apply", False)
    if not apply:
        try:
            confirm = input("\n是否更新？[y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            confirm = "n"
        if confirm != "y":
            print("已取消。")
            return

    from .adapters.updater import AutoUpdater

    updater = AutoUpdater(repo, checker)
    applied = updater._check_and_apply()
    print(f"\n更新完成: {len(applied)} 个模板已更新。")


# ======================================================================
# 子命令: batch
# ======================================================================

def cmd_batch(args: argparse.Namespace) -> None:
    """批量矫正多个文件"""
    from .services.batch_service import BatchCorrectionService

    input_path = Path(args.input_dir)
    output_path = Path(args.output_dir)

    # 加载配置
    corrector_app = PaperFormatCorrector(args.config, args.log_level)
    if args.preset:
        corrector_app.apply_preset(args.preset)
    if args.requirement:
        corrector_app.apply_requirement(args.requirement, use_llm=args.llm,
                                        use_offline_parser=args.offline_parser,
                                        llm_provider=args.llm_provider,
                                        llm_api_key=args.llm_key)

    batch_service = BatchCorrectionService(corrector_app.config, args.log_level)

    def progress(current, total, filename):
        print(f"  [{current}/{total}] {filename}")

    # 异步模式：将文件提交到任务队列
    if getattr(args, 'async_mode', False):
        print("\n异步批量处理模式")
        files = list(input_path.rglob("*")) if input_path.is_dir() else [Path(args.input_dir)]
        files = [f for f in files if f.is_file() and f.suffix.lower() in ('.docx', '.doc', '.txt', '.md')]
        task_ids = batch_service.async_process_files(
            [str(f) for f in files], output_path,
            score=args.score,
            progress_callback=progress,
        )
        print(f"\n已提交 {len(task_ids)} 个任务到队列")
        for tid in task_ids:
            print(f"  任务ID: {tid}")
        print("\n使用 API 查询任务状态: GET /tasks/{task_id}")
        return

    if input_path.is_dir():
        print(f"\n批量处理目录: {input_path}")
        summary = batch_service.process_directory(
            input_path, output_path,
            score=args.score,
            progress_callback=progress,
        )
    else:
        print("\n批量处理文件列表...")
        files = [args.input_dir]  # 假设是文件路径
        summary = batch_service.process_files(
            files, output_path,
            score=args.score,
            progress_callback=progress,
        )

    print("\n处理完成!")
    print(f"  成功: {summary.success_count}/{summary.total_files}")
    print(f"  失败: {summary.failed_count}")
    print(f"  耗时: {summary.total_processing_time:.1f}s")
    if summary.avg_quality_score > 0:
        print(f"  平均评分: {summary.avg_quality_score:.1f}/100")


# ======================================================================
# 子命令: report
# ======================================================================

def cmd_report(args: argparse.Namespace) -> None:
    """生成或查看报告"""
    from .services.report_service import ReportData, ReportService

    if args.report_id:
        # 查看历史报告
        from .adapters.storage.template_repository import TemplateRepository
        _repo = TemplateRepository()
        detail = _repo.get_processing_history(int(args.report_id))
        if detail is None:
            print(f"未找到报告 ID: {args.report_id}")
        else:
            print(f"报告详情 (ID: {args.report_id}):")
            print(f"  输入文件: {detail.get('input_file', '')}")
            print(f"  输出文件: {detail.get('output_file', '')}")
            print(f"  模板: {detail.get('template_used', '')}")
            print(f"  评分: {detail.get('quality_score', 0)}")
            print(f"  处理时间: {detail.get('processing_time', 0):.1f}s")
        return

    if not args.file:
        print("错误: 请指定输入文件 (-f)")
        sys.exit(1)

    # 生成报告
    path = Path(args.file)
    if not path.is_file():
        print(f"错误: 文件不存在: {args.file}")
        sys.exit(1)

    from .core.quality.quality_scorer import QualityScorer

    print(f"\n生成报告: {path.name}")
    print("=" * 60)

    # 先矫正（如果指定了输出）
    output_path = Path(args.output) if args.output else Path("output") / f"report_{path.stem}.docx"

    corrector_app = PaperFormatCorrector(args.config, args.log_level)
    if args.preset:
        corrector_app.apply_preset(args.preset)
    if args.requirement:
        corrector_app.apply_requirement(args.requirement, use_llm=args.llm,
                                        use_offline_parser=args.offline_parser,
                                        llm_provider=args.llm_provider,
                                        llm_api_key=args.llm_key)

    try:
        report = corrector_app.corrector.correct_document(str(path), str(output_path))
    except Exception as e:
        print(f"矫正失败: {e}")
        sys.exit(1)

    # 评分
    quality_score = 0.0
    if args.score:
        try:
            scorer = QualityScorer(corrector_app.config)
            total, _, _ = scorer.score(str(output_path))
            quality_score = total
        except Exception:
            pass

    # 生成报告
    report_data = ReportData(
        input_file=str(path),
        output_file=str(output_path),
        template_used=args.preset or "默认配置",
        processing_time=report.get("processing_time", 0),
        quality_score=quality_score,
        applied={
            "paragraphs": report.get("paragraphs_corrected", 0),
            "headings": report.get("headings_fixed", 0),
            "body": report.get("body_fixed", 0),
            "tables": report.get("tables_formatted", 0),
            "images": report.get("images_centered", 0),
        },
        skipped=report.get("skipped_items", []),
        warnings=report.get("warnings", []),
        risk_items=report.get("risk_items", []),
        rule_sources=report.get("rule_sources", {}),
    )

    svc = ReportService()
    fmt = args.format if hasattr(args, "format") and args.format else "html"
    report_path = output_path.with_suffix(f".{fmt}")
    svc.save_report(report_data, report_path, fmt=fmt)
    print(f"报告已保存: {report_path}")


# ======================================================================
# 向后兼容的子命令 (原有 -f 等参数模式)
# ======================================================================

def _handle_generate(args) -> None:  # noqa: C901
    """处理AI文档生成"""
    user_input = args.generate
    if not user_input:
        print("\n请输入文档描述（输入空行结束）：")
        lines = []
        while True:
            try:
                line = input()
                if not line:
                    break
                lines.append(line)
            except EOFError:
                break
        user_input = "\n".join(lines)

    if not user_input.strip():
        print("错误：未提供文档描述")
        sys.exit(1)

    print(f"\n文档描述: {user_input}")
    print(f"文档类型: {args.doc_type}")
    print()

    template_config = None
    if args.doc_template:
        try:
            template_config = load_doc_template(args.doc_template)
            print(f"使用模板: {args.doc_template}")
        except FileNotFoundError as e:
            print(f"警告: {e}")

    try:
        from paper_format_corrector.core.document.ai_doc_generator import AIDocGenerator
        ai_gen = AIDocGenerator(
            provider=args.gen_provider,
            api_key=args.gen_key,
            base_url=args.gen_base_url,
            model=args.gen_model,
            allow_custom_base_url=True,
        )
    except Exception as e:
        print(f"错误: 无法创建AI生成器: {e}")
        sys.exit(1)

    if args.stream:
        print("正在调用AI生成文档内容（流式模式）...\n")
        try:
            print("=" * 60)
            print("AI生成内容（实时输出）:")
            print("=" * 60)
            for chunk in ai_gen.generate_structure_stream(user_input, args.doc_type):
                print(chunk, end="", flush=True)
            print("\n" + "=" * 60)
            print("AI生成完成！")
            structure = ai_gen.session.outline.get("structure", {})
            if not structure:
                structure = ai_gen.generate_structure(user_input, args.doc_type)
        except Exception as e:
            print(f"\n错误: AI生成失败: {e}")
            sys.exit(1)
    else:
        print("正在调用AI生成文档内容...")
        try:
            structure = ai_gen.generate_structure(user_input, args.doc_type)
        except Exception as e:
            print(f"错误: AI生成失败: {e}")
            sys.exit(1)
        print("AI生成完成！")

    print("\n正在创建Word文档...")
    output_path = Path("output") / "generated_document.docx"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        format_rules = template_config.get("format_rules", {}) if template_config else {}
        doc_gen = DocGenerator(format_rules)
        doc_gen.generate(structure, str(output_path))
        print(f"\n文档已生成: {output_path.resolve()}")
        print(f"标题: {structure.get('title', '未命名')}")
        print(f"段落数: {len(structure.get('sections', []))}")
    except Exception as e:
        print(f"错误: 文档生成失败: {e}")
        sys.exit(1)


def _handle_list_models(args) -> None:
    """列出当前provider下所有可用模型"""
    from .core.document.model_discovery import list_models

    provider = args.llm_provider
    api_key = args.llm_key
    base_url = args.llm_base_url

    print(f"\n正在查询 {provider} 的可用模型...")
    if base_url:
        print(f"  端点: {base_url}")
    print()

    models = list_models(provider, api_key, base_url)

    if not models:
        print("  未找到可用模型。请检查：")
        if provider != "ollama":
            print("  - API Key 是否已配置（环境变量或 --llm-key）")
        else:
            print("  - Ollama 服务是否在运行（ollama serve）")
            print("  - 是否已下载模型（ollama pull <model>）")
        return

    print(f"  找到 {len(models)} 个可用模型:")
    print("  " + "-" * 56)
    for m in models:
        print(f"  {m}")
    print("  " + "-" * 56)
    print("\n  提示: 使用 --probe-model <model_name> 探测指定模型的延迟和可用性")
    print(f"  用法: python -m paper_format_corrector --list-models --llm-provider {provider}")


def _handle_probe_model(args) -> None:
    """探测指定模型是否可用"""
    from .core.document.model_discovery import probe_model

    provider = args.llm_provider
    api_key = args.llm_key
    base_url = args.llm_base_url
    model_names = args.probe_model

    print(f"\n探测模型可用性 ({provider})...")
    if base_url:
        print(f"  端点: {base_url}")
    print()

    for model_name in model_names:
        model_name = model_name.strip()
        if not model_name:
            continue
        print(f"  测试: {model_name} ...", end=" ", flush=True)
        result = probe_model(provider, model_name, api_key, base_url)

        if result["available"]:
            latency = f'{result["latency_ms"]}ms' if result["latency_ms"] else "N/A"
            print(f"✓ 可用  (延迟: {latency})")
        else:
            error = result.get("error", "未知错误")
            print(f"✗ 不可用 - {error}")

    print()
    print("  提示: 可以使用任意模型名（不限于官方列表）")
    print("  用法: python -m paper_format_corrector --probe-model deepseek-chat qwen-plus --llm-provider openai")


def _handle_interactive_chat(args) -> None:  # noqa: C901
    """处理交互式AI对话"""
    from .core.document.ai_doc_generator import AIDocGenerator

    try:
        ai_gen = AIDocGenerator(
            provider=args.gen_provider,
            api_key=args.gen_key,
            model=args.gen_model,
        )
    except Exception as e:
        print(f"错误: 无法创建AI生成器: {e}")
        sys.exit(1)

    print("=" * 60)
    print("  AI文档生成 - 交互式对话模式")
    print("=" * 60)
    print("输入文档描述开始对话，输入 'quit' 或 'exit' 退出")
    print("输入 'confirm' 确认大纲，输入 'reset' 重新开始")
    print()

    while True:
        try:
            user_input = input("你: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\n再见！")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("\n再见！")
            break
        if user_input.lower() == "reset":
            ai_gen.reset_session()
            print("[系统] 会话已重置\n")
            continue

        try:
            if ai_gen.session.outline is None:
                print("\n[系统] 正在生成大纲...")
                outline = ai_gen.generate_outline(user_input, args.doc_type or "通用文档")

                print(f"\nAI: 识别的文档类型: {outline.get('doc_type', '未知')}")
                print(f"    文档标题: {outline.get('title', '未知')}")
                print(f"    摘要: {outline.get('abstract', '')}")
                print("\n    大纲结构:")
                for item in outline.get("outline", []):
                    item_type = item.get("type", "")
                    title = item.get("title", "")
                    desc = item.get("description", "")
                    indent = "      " if "2" in item_type or "3" in item_type else "    "
                    print(f"    {indent}{title}")
                    if desc:
                        print(f"    {indent}  ({desc})")
                print()
                print("[提示] 输入 'confirm' 确认大纲，或告诉我需要修改的地方")

            elif not ai_gen.session.outline.get("structure"):
                if "confirm" in user_input.lower() or "确认" in user_input:
                    ai_gen.confirm_outline(True)
                    print("\n[系统] 大纲已确认，开始生成文档内容...\n")

                    structure = ai_gen.generate_structure(
                        ai_gen.session.outline.get("title", ""),
                        args.doc_type or "通用文档",
                    )
                    ai_gen.session.outline["structure"] = structure

                    doc_gen = DocGenerator()
                    preview = doc_gen.generate_preview(structure)
                    print(f"AI: 文档生成完成！\n\n预览:\n{preview[:500]}...\n")

                    output_path = Path("output") / "generated_document.docx"
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    doc_gen.generate(structure, str(output_path))
                    print(f"[系统] 文档已保存: {output_path.resolve()}")
                    print("[提示] 输入 'reset' 生成新文档，或告诉我需要修改的内容")
                else:
                    print("\nAI: 请告诉我需要调整的内容，或输入 'confirm' 确认大纲")

            else:
                print("\nAI: 文档已生成完成。")
                print("    你可以：")
                print("    1. 输入 'reset' 生成新文档")
                print("    2. 告诉我需要修改的内容")
                print("    3. 输入 'quit' 退出")

        except Exception as e:
            print(f"\n错误: {e}")
            print("[提示] 请检查API配置后重试")


# ======================================================================
# 主入口
# ======================================================================

def _add_common_args(parser: argparse.ArgumentParser) -> None:
    """添加通用参数"""
    parser.add_argument("-c", "--config", default="config/config.yaml", help="配置文件路径")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])


def _add_preset_args(parser: argparse.ArgumentParser) -> None:
    """添加预设和需求文档参数"""
    preset_choices = get_preset_choices()
    parser.add_argument("--preset", choices=preset_choices if preset_choices else None,
                        help=f"格式预设: {', '.join(preset_choices)}")
    parser.add_argument("-r", "--requirement", help="需求文档路径")
    parser.add_argument("--llm", action="store_true", help="使用LLM智能解析需求文档")
    parser.add_argument("--offline-parser", action="store_true", help="使用离线规则解析器")
    parser.add_argument("--llm-provider", default="openai", choices=["openai", "anthropic", "ollama"])
    parser.add_argument("--llm-key", help="LLM API Key")
    parser.add_argument("--llm-model", help="LLM模型名称")


# ======================================================================
# 子命令: db (数据库管理)
# ======================================================================

def cmd_database(args: argparse.Namespace) -> None:
    """数据库管理子命令"""
    from paper_format_corrector.adapters.database import (
        DatabaseManager, initialize_database, MySQLReportRepository,
    )

    action = getattr(args, "db_action", "init")
    db = DatabaseManager.from_config_file(args.config)

    if action == "init":
        print(f"\n初始化数据库: {db.database_name}")
        print("=" * 50)
        try:
            count = initialize_database(db)
            print(f"\n数据库 '{db.database_name}' 初始化完成")
            print(f"已创建/更新 {count} 张表")
            print("\n表列表:")
            with db.cursor() as cur:
                cur.execute("SHOW TABLES")
                for row in cur.fetchall():
                    table_name = list(row.values())[0]
                    print(f"  - {table_name}")
        except Exception as e:
            print(f"\n初始化失败: {e}")
            print("请检查 MySQL 服务是否启动，以及配置是否正确")
            sys.exit(1)

    elif action == "test":
        print(f"\n测试数据库连接: {db.get_full_params()['host']}:{db.get_full_params()['port']}")
        print("=" * 50)
        result = db.test_connection()
        if result["connected"]:
            print(f"连接成功!")
            print(f"  MySQL 版本: {result['mysql_version']}")
            print(f"  当前数据库: {result['database']}")
        else:
            print(f"连接失败: {result['error']}")
            sys.exit(1)

    elif action == "status":
        print(f"\n数据库状态: {db.database_name}")
        print("=" * 50)
        result = db.test_connection()
        if not result["connected"]:
            print(f"无法连接: {result['error']}")
            sys.exit(1)

        print(f"MySQL 版本: {result['mysql_version']}")
        with db.cursor() as cur:
            # 统计各表记录数
            tables = ["templates", "reports", "ai_conversations", "ai_messages",
                      "plugins", "format_rules", "settings"]
            print(f"\n表记录统计:")
            for table in tables:
                try:
                    cur.execute(f"SELECT COUNT(*) as cnt FROM `{table}`")
                    row = cur.fetchone()
                    count = row["cnt"] if row else 0
                    print(f"  {table:<20} {count:>6} 条记录")
                except Exception:
                    print(f"  {table:<20} (不存在)")

    elif action == "stats":
        print(f"\n报告统计: {db.database_name}")
        print("=" * 50)
        repo = MySQLReportRepository(db)
        stats = repo.get_statistics(days=30)
        if not stats:
            print("暂无报告数据")
            return

        print(f"\n最近 30 天统计:")
        print(f"  总报告数: {stats.get('total_reports', 0)}")
        print(f"  成功数:   {stats.get('success_count', 0)}")
        print(f"  失败数:   {stats.get('error_count', 0)}")
        print(f"  成功率:   {stats.get('success_rate', 0)}%")
        print(f"  平均评分: {stats.get('avg_quality_score', 0)}")
        print(f"  平均耗时: {stats.get('avg_processing_time_ms', 0):.0f}ms")

        presets = repo.get_preset_usage(limit=5)
        if presets:
            print(f"\n热门预设:")
            for p in presets:
                print(f"  {p['preset_name']:<20} 使用 {p['usage_count']} 次")


def main() -> None:  # noqa: C901
    """CLI 主入口"""
    parser = argparse.ArgumentParser(
        description="论文格式自动矫正工具 v3.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
子命令模式 (推荐):
  python -m paper_format_corrector scan -f paper.docx
  python -m paper_format_corrector correct -f paper.docx --preset ieee
  python -m paper_format_corrector learn -f sample.docx -o rules.json
  python -m paper_format_corrector template list
  python -m paper_format_corrector template import file.yaml
  python -m paper_format_corrector template export builtin-ieee -o ieee.yaml
  python -m paper_format_corrector template delete personal-my-template
  python -m paper_format_corrector template update
  python -m paper_format_corrector batch -i input/ -o output/
  python -m paper_format_corrector report -f paper.docx --score

平铺参数模式 (向后兼容):
  python -m paper_format_corrector -f paper.docx --preset ieee
  python -m paper_format_corrector --gui
  python -m paper_format_corrector --desktop-gui
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # --- scan ---
    scan_parser = subparsers.add_parser("scan", help="扫描文档结构和样式")
    scan_parser.add_argument("-f", "--file", required=True, help="文档路径")
    _add_common_args(scan_parser)

    # --- correct ---
    correct_parser = subparsers.add_parser("correct", help="矫正单个论文")
    correct_parser.add_argument("-f", "--file", required=True, help="文档路径")
    correct_parser.add_argument("-o", "--output", help="输出路径")
    correct_parser.add_argument("-t", "--template", help="模板文件路径")
    correct_parser.add_argument("--no-template", action="store_true", help="不使用模板")
    correct_parser.add_argument("--language", choices=["auto", "chinese", "english", "japanese", "korean"],
                                default="auto", help="文档语言 (默认: auto)")
    correct_parser.add_argument("--score", action="store_true", help="输出质量评分")
    correct_parser.add_argument("--diff", action="store_true", help="生成对比报告")
    correct_parser.add_argument("--format", nargs="+", help="额外导出格式: pdf html txt md")
    _add_preset_args(correct_parser)
    _add_common_args(correct_parser)

    # --- learn ---
    learn_parser = subparsers.add_parser("learn", help="从样本文档学习格式")
    learn_parser.add_argument("-f", "--file", required=True, help="样本文档路径")
    learn_parser.add_argument("-o", "--output", help="保存规则到JSON文件")
    _add_common_args(learn_parser)

    # --- template ---
    template_parser = subparsers.add_parser("template", help="模板管理")
    template_sub = template_parser.add_subparsers(dest="template_action", help="模板操作")

    # template list
    list_parser = template_sub.add_parser("list", help="列出模板")
    list_parser.add_argument("--category", help="按分类筛选")
    list_parser.add_argument("--search", help="搜索关键词")
    list_parser.add_argument("--all", action="store_true", help="显示所有模板(含禁用)")
    _add_common_args(list_parser)

    # template import
    import_parser = template_sub.add_parser("import", help="导入模板")
    import_parser.add_argument("file", help="模板文件路径 (.yaml/.json)")
    _add_common_args(import_parser)

    # template export
    export_parser = template_sub.add_parser("export", help="导出模板")
    export_parser.add_argument("slug", help="模板Slug")
    export_parser.add_argument("-o", "--output", help="输出路径")
    export_parser.add_argument("--format", choices=["yaml", "json"], default="yaml", help="导出格式")
    _add_common_args(export_parser)

    # template delete
    delete_parser = template_sub.add_parser("delete", help="删除个人模板")
    delete_parser.add_argument("slug", help="模板Slug")
    _add_common_args(delete_parser)

    # template info
    info_parser = template_sub.add_parser("info", help="查看模板详情")
    info_parser.add_argument("slug", help="模板Slug")
    _add_common_args(info_parser)

    # template update
    update_parser = template_sub.add_parser("update", help="检查云端模板更新")
    update_parser.add_argument("--remote-url", help="远程仓库地址（覆盖配置）")
    update_parser.add_argument("--apply", action="store_true", help="自动应用所有更新")
    _add_common_args(update_parser)

    # --- batch ---
    batch_parser = subparsers.add_parser("batch", help="批量矫正多个文件")
    batch_parser.add_argument("-i", "--input-dir", required=True, help="输入目录或文件")
    batch_parser.add_argument("-o", "--output-dir", default="output", help="输出目录")
    batch_parser.add_argument("--score", action="store_true", help="输出质量评分")
    batch_parser.add_argument("--async", dest="async_mode", action="store_true", help="异步模式：提交到任务队列")
    _add_preset_args(batch_parser)
    _add_common_args(batch_parser)

    # --- report ---
    report_parser = subparsers.add_parser("report", help="生成或查看报告")
    report_parser.add_argument("-f", "--file", help="文档路径")
    report_parser.add_argument("-o", "--output", help="报告输出路径")
    report_parser.add_argument("--format", choices=["html", "md", "json"], default="html")
    report_parser.add_argument("--score", action="store_true", help="输出质量评分")
    report_parser.add_argument("--report-id", help="查看历史报告ID")
    _add_preset_args(report_parser)
    _add_common_args(report_parser)

    # --- db (数据库管理) ---
    db_parser = subparsers.add_parser("db", help="数据库管理")
    db_parser.add_argument("db_action", nargs="?", default="init",
                           choices=["init", "test", "status", "stats"],
                           help="操作: init=初始化, test=测试连接, status=状态, stats=统计")
    _add_common_args(db_parser)

    # --- 向后兼容的平铺参数模式 ---
    _add_common_args(parser)
    parser.add_argument("-f", "--file", dest="flat_file", help="处理单个文件路径")
    parser.add_argument("-o", "--output", dest="flat_output", help="输出文件路径")
    parser.add_argument("-i", "--input-dir", dest="flat_input_dir", default="input")
    parser.add_argument("-d", "--output-dir", dest="flat_output_dir", default="output")
    parser.add_argument("-t", "--template", dest="flat_template")
    parser.add_argument("--no-template", action="store_true")
    parser.add_argument("--preset", dest="flat_preset")
    parser.add_argument("--list-presets", action="store_true")
    parser.add_argument("-r", "--requirement", dest="flat_requirement")
    parser.add_argument("--llm", action="store_true")
    parser.add_argument("--offline-parser", action="store_true")
    parser.add_argument("--llm-provider", default="openai", choices=["openai", "anthropic", "ollama"])
    parser.add_argument("--llm-key")
    parser.add_argument("--llm-model")
    parser.add_argument("--list-models", action="store_true")
    parser.add_argument("--probe-model", nargs="+", metavar="MODEL")
    parser.add_argument("--llm-base-url")
    parser.add_argument("--format", dest="flat_format", nargs="+")
    parser.add_argument("--score", action="store_true")
    parser.add_argument("--diff", action="store_true")
    parser.add_argument("--rules")
    parser.add_argument("--cover", nargs="*")
    parser.add_argument("--generate", nargs="?", const="")
    parser.add_argument("--stream", action="store_true")
    parser.add_argument("--chat", action="store_true")
    parser.add_argument("--doc-type", default="通用文档",
                        choices=["通用文档", "报告", "公文", "合同", "论文", "方案", "会议纪要", "可行性报告", "项目立项", "工作总结", "调研报告"])
    parser.add_argument("--doc-template")
    parser.add_argument("--list-doc-templates", action="store_true")
    parser.add_argument("--gen-provider", default="deepseek",
                        choices=["openai", "anthropic", "ollama", "deepseek", "qwen", "zhipu",
                                 "moonshot", "baichuan", "stepfun", "lingyiwanwu", "minimax",
                                 "xunfei", "siliconflow", "custom"],
                        help="LLM提供商 (默认: deepseek)")
    parser.add_argument("--gen-key", help="LLM API Key")
    parser.add_argument("--gen-model", help="模型名称")
    parser.add_argument("--gen-base-url", help="自定义 API 地址 (如 https://api.deepseek.com/v1)")
    parser.add_argument("--gui", action="store_true")
    parser.add_argument("--desktop-gui", action="store_true")
    parser.add_argument("--extract", action="store_true")
    parser.add_argument("--workers", type=int, default=None)

    args = parser.parse_args()

    print("=" * 60)
    print("  论文格式自动矫正工具 v3.0")
    print("=" * 60)

    for dir_name in ("template", "input", "output"):
        Path(dir_name).mkdir(exist_ok=True)

    # ----- 子命令模式 -----
    if args.command == "scan":
        cmd_scan(args)
        return

    if args.command == "correct":
        _cmd_correct(args)
        return

    if args.command == "learn":
        cmd_learn(args)
        return

    if args.command == "template":
        cmd_template(args)
        return

    if args.command == "batch":
        cmd_batch(args)
        return

    if args.command == "report":
        cmd_report(args)
        return

    if args.command == "db":
        cmd_database(args)
        return

    # ----- 向后兼容的平铺参数模式 -----
    _run_flat_mode(args)


def _cmd_correct(args: argparse.Namespace) -> None:
    """执行单文件矫正子命令"""
    corrector = PaperFormatCorrector(args.config, args.log_level)

    # Apply language setting if specified
    language = getattr(args, "language", "auto")
    if language and language != "auto":
        from ...services.style_workbench import get_language_font_config
        lang_fonts = get_language_font_config(language)
        if lang_fonts.get("body_font"):
            corrector.config.setdefault("format_rules", {}).setdefault("font", {})
            corrector.config["format_rules"]["font"]["chinese"] = lang_fonts["body_font"]
            corrector.config["format_rules"]["font"]["heading_chinese"] = lang_fonts["heading_font"]
            corrector.config["format_rules"]["font"]["english"] = lang_fonts["en_font"]
            print(f"\n语言: {language} — 正文: {lang_fonts['body_font']}, 标题: {lang_fonts['heading_font']}")

    if args.preset:
        print(f"\n应用格式预设: {args.preset}")
        corrector.apply_preset(args.preset)

    if args.requirement:
        print(f"\n解析需求文档: {args.requirement}")
        corrector.apply_requirement(
            args.requirement, use_llm=args.llm,
            use_offline_parser=args.offline_parser,
            llm_provider=args.llm_provider,
            llm_api_key=args.llm_key, llm_model=args.llm_model,
        )

    if args.no_template:
        corrector.template_path = ""
        corrector.corrector = FormatCorrector("", corrector.config)
    elif args.template:
        corrector.template_path = args.template
        corrector.corrector = FormatCorrector(args.template, corrector.config)

    corrector.process_single(args.file, args.output, args.format, args.score, args.diff)
    print("\n处理完成！")


def _run_flat_mode(args: argparse.Namespace) -> None:
    """向后兼容的平铺参数模式"""
    corrector = PaperFormatCorrector(args.config, args.log_level)

    if args.flat_preset:
        print(f"\n应用格式预设: {args.flat_preset}")
        corrector.apply_preset(args.flat_preset)
        print()

    if args.flat_requirement:
        print(f"\n解析需求文档: {args.flat_requirement}")
        corrector.apply_requirement(
            args.flat_requirement, use_llm=args.llm,
            use_offline_parser=args.offline_parser,
            llm_provider=args.llm_provider,
            llm_api_key=args.llm_key, llm_model=args.llm_model,
        )
        print()

    if args.flat_template:
        corrector.template_path = args.flat_template
        corrector.corrector = FormatCorrector(args.flat_template, corrector.config)

    if args.list_presets:
        print(format_preset_list())
        return

    if args.list_doc_templates:
        templates = list_doc_templates()
        if not templates:
            print("未找到文档模板。")
            return
        print("\n可用的文档模板:")
        print("-" * 60)
        for t in templates:
            hints = ", ".join(t.get("doc_type_hints", [])[:3])
            print(f"  {t['name']:<25s} {t['description']}")
            if hints:
                print(f"  {'':25s} 适用类型: {hints}")
        print("-" * 60)
        return

    if args.list_models:
        _handle_list_models(args)
        return

    if args.probe_model:
        _handle_probe_model(args)
        return

    if args.gui:
        try:
            from ..web.app import main as gui_main
            gui_main()
        except ImportError:
            print("Web GUI需要安装gradio: pip install gradio")
        return

    if args.desktop_gui:
        try:
            from ..desktop.app import main as desktop_main
            desktop_main()
        except ImportError:
            print("桌面 GUI 需要安装 tkinterdnd2: pip install tkinterdnd2")
            sys.exit(1)
        return

    if args.extract:
        corrector.extract_template_info()
        return

    if args.cover is not None:
        metadata = {}
        for item in args.cover:
            if "=" in item:
                k, v = item.split("=", 1)
                metadata[k] = v
        if not metadata:
            from datetime import datetime
            now = datetime.now()
            metadata = {
                "title": "论文题目", "author": "作者姓名",
                "college": "学院名称", "major": "专业名称",
                "date": f"{now.year}年{now.month}月",
            }
        cover_path = Path("output") / "cover.docx"
        corrector.generate_cover(metadata, str(cover_path))
        return

    if args.chat:
        _handle_interactive_chat(args)
        return

    if args.generate is not None:
        _handle_generate(args)
        return

    if args.rules and args.flat_file:
        corrector.check_rules(args.flat_file, rules_path=args.rules)
        return

    if args.flat_file:
        if args.flat_output:
            from .adapters.path_security import ALLOWED_OUTPUT_EXTENSIONS, validate_output_path
            validate_output_path(args.flat_output, ALLOWED_OUTPUT_EXTENSIONS)
        corrector.process_single(args.flat_file, args.flat_output, args.flat_format, args.score, args.diff)
    else:
        if corrector.template_path and not Path(corrector.template_path).exists():
            corrector.logger.warning(f"模板文件不存在 ({corrector.template_path})")
        corrector.process_directory(args.flat_input_dir, args.flat_output_dir, args.flat_format, args.score, args.workers)

    print("\n处理完成！")


if __name__ == "__main__":
    main()
