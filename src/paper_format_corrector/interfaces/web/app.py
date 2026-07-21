"""论文格式矫正工具 - Web GUI v2

基于 Gradio 的可视化界面，提供：
- 上传论文文件
- 上传需求文档（可选）
- 一键矫正
- 实时质量评分
- 对比报告预览
- 下载矫正结果
- AI文档生成（对话式，流式输出）

启动方式：
    python -m paper_format_corrector.gui
    或
    python -m paper_format_corrector --gui
"""

import atexit
import json
import logging
import shutil
import tempfile
from pathlib import Path
from typing import Any

try:
    import gradio as gr
except ImportError:
    print("请先安装 Gradio: pip install gradio")
    print("然后运行: python -m paper_format_corrector.gui")
    exit(1)

from ...app import PaperFormatCorrector
from ...application.style_workbench import (
    build_application_report,
    explain_style_profile,
    get_language_font_config,
    learn_style_profile,
    manual_style_config,
    scan_document,
    LANGUAGE_FONT_PRESETS,
)
from ...domain.correction.doc_generator import DocGenerator
from ...infrastructure.converters.file_converter import FileConverter
from ...infrastructure.converters.file_formatter import FormatCorrector
from ...infrastructure.exporters.format_exporter import FormatExporter
from ...infrastructure.generators.cover_generator import CoverPageGenerator
from ...infrastructure.doc_template_loader import list_doc_templates
from ...infrastructure.preset_loader import list_presets
from ...infrastructure.template_repository import TemplateRepository
from ...domain.quality.diff_reporter import DiffReporter
from ...domain.quality.quality_scorer import QualityScorer

# 全局实例
corrector = None
config_path = "config/config.yaml"

# 临时目录跟踪（退出时清理）
_temp_dirs: list[str] = []

# AI文档生成器实例（按会话管理）
_ai_sessions: dict[str, dict] = {}

# session 最大数量限制
_MAX_SESSIONS = 50


def _cleanup_temp_dirs():
    for d in _temp_dirs:
        shutil.rmtree(d, ignore_errors=True)
    _temp_dirs.clear()


atexit.register(_cleanup_temp_dirs)

# 预设名称 -> ID 映射（避免字符串解析出错）
_PRESET_MAP = {}
for _p in list_presets():
    _PRESET_MAP[f"{_p['name']} - {_p['description']}"] = _p['name']


def _template_repository() -> TemplateRepository:
    return TemplateRepository()


def workbench_template_choices() -> list[str]:
    """Build stable dropdown values while displaying source/category to users."""
    choices = ["无（使用默认配置）"]
    for template in _template_repository().list_templates():
        choices.append(f"{template.slug} | [{template.category}] {template.name}")
    return choices


def _load_workbench_template(choice: str) -> dict:
    if not choice or choice == "无（使用默认配置）":
        return {}
    slug = choice.split(" | ", 1)[0]
    template = _template_repository().get(slug)
    if template is None:
        raise ValueError("所选模板不存在，请刷新模板库后重试")
    return template.config



def init_corrector(config_file=None):
    global corrector, config_path
    if config_file:
        config_path = config_file
    corrector = PaperFormatCorrector(config_path)
    return corrector


def process_paper(paper_file, requirement_file, config_file, template_file, preset_name, export_formats, do_score, do_diff):  # noqa: C901
    """处理论文主函数"""
    if paper_file is None:
        return None, None, "请上传论文文件", None

    # 校验论文文件扩展名
    from .infrastructure.path_security import ALLOWED_INPUT_EXTENSIONS
    paper_ext = Path(paper_file.name).suffix.lower()
    if paper_ext not in ALLOWED_INPUT_EXTENSIONS:
        return None, None, f"不支持的文件类型: {paper_ext}", None

    # 初始化
    try:
        cfg = config_file.name if config_file else config_path
        c = PaperFormatCorrector(cfg)
    except Exception:
        return None, None, "配置加载失败，请检查配置文件格式。", None

    # 覆盖模板文件
    if template_file:
        tpl_path = template_file.name
        if not tpl_path.lower().endswith('.docx'):
            return None, None, "模板文件必须是 .docx 格式", None
        try:
            c.template_path = tpl_path
            c.corrector = FormatCorrector(tpl_path, c.config)
        except Exception:
            return None, None, "模板文件加载失败，请检查文件是否为有效的 .docx 文件。", None

    # 应用格式预设
    if preset_name and preset_name != "无 (使用默认配置)":
        try:
            preset_id = _PRESET_MAP.get(preset_name, preset_name)
            c.apply_preset(preset_id)
        except Exception:
            return None, None, "预设加载失败，请检查预设名称。", None

    # 应用需求文档
    if requirement_file:
        try:
            c.apply_requirement(requirement_file.name)
        except Exception:
            return None, None, "需求文档解析失败，请检查文件格式。", None

    # 输出路径
    output_dir = Path(tempfile.mkdtemp())
    _temp_dirs.append(str(output_dir))
    input_path = Path(paper_file.name)

    # 格式转换（如果需要）
    converter = FileConverter()
    if converter.needs_conversion(str(input_path)):
        try:
            converted_path = converter.convert(str(input_path), str(output_dir))
            input_path = Path(converted_path)
        except Exception:
            return None, None, "文件格式转换失败，请检查文件格式是否支持。", None

    output_path = output_dir / f"formatted_{input_path.name}"

    # 处理
    try:
        report = c.corrector.correct_document(str(input_path), str(output_path))
    except Exception:
        return None, None, "处理失败，请检查论文文件是否为有效的 .docx 文件。", None

    # 质量评分
    score_report = ""
    if do_score:
        scorer = QualityScorer(c.config)
        total, scores, issues = scorer.score(str(output_path))
        score_report = scorer.format_report(total, scores, issues)

    # 对比报告
    diff_path = None
    if do_diff:
        diff_path = str(output_path.with_suffix(".diff.html"))
        reporter = DiffReporter()
        # 复制原始文件
        orig_path = str(output_path) + ".orig.docx"
        shutil.copy2(str(input_path), orig_path)
        reporter.generate_html_report(orig_path, str(output_path), diff_path)
        Path(orig_path).unlink(missing_ok=True)

    # 导出
    exported_files = []
    if export_formats:
        exporter = FormatExporter()
        for fmt in export_formats:
            fmt = fmt.lower().strip()
            if fmt in ("docx", "doc"):
                continue
            out = output_path.with_suffix(f".{fmt}")
            try:
                exporter.export(str(output_path), str(out), fmt)
                exported_files.append(str(out))
            except Exception:
                pass

    # 处理报告文本
    report_text = format_report_text(report)

    return str(output_path), score_report, report_text, diff_path


def format_report_text(report):
    lines = []
    lines.append(f"矫正段落数: {report['paragraphs_corrected']}")
    lines.append(f"标题矫正:   {report['headings_fixed']}")
    lines.append(f"正文矫正:   {report['body_fixed']}")
    if report.get("tables_formatted"):
        lines.append(f"表格格式化: {report['tables_formatted']}")
    if report.get("images_centered"):
        lines.append(f"图片居中:   {report['images_centered']}")
    if report.get("fig_table_issues"):
        lines.append(f"\n图表编号修正 ({len(report['fig_table_issues'])}):")
        for issue in report["fig_table_issues"]:
            lines.append(f"  - {issue}")
    if report.get("citation_style"):
        lines.append(f"\n检测到引用风格: {report['citation_style']}")
    if report.get("ref_issues"):
        lines.append(f"\n参考文献问题 ({len(report['ref_issues'])}):")
        for issue in report["ref_issues"]:
            lines.append(f"  - {issue}")
    return "\n".join(lines)


def update_font_preview(language):
    """Return font preview text based on selected language."""
    if not language or language == "auto":
        return "语言: 自动检测\n正文字体: 将根据文档内容自动选择\n标题字体: 将根据文档内容自动选择\n英文字体: Times New Roman"
    cfg = get_language_font_config(language)
    preset = LANGUAGE_FONT_PRESETS.get(language, {})
    lines = [
        f"语言: {preset.get('label', language)}",
        f"正文字体: {cfg['body_font']}",
        f"标题字体: {cfg['heading_font']}",
        f"英文字体: {cfg['en_font']}",
        f"\n提示: 选择语言后，下方的字体字段将自动填充。",
        f"您也可以手动修改字体来覆盖默认值。",
    ]
    return "\n".join(lines)


def scan_workbench_document(paper_file):
    """Scan a document before applying a workbench style."""
    if paper_file is None:
        return "请先上传 .docx 论文。"
    try:
        inventory = scan_document(paper_file.name)
        return json.dumps(inventory, ensure_ascii=False, indent=2)
    except Exception as exc:
        return f"扫描失败：{exc}"


# 全局存储低置信度扫描结果和用户修正
_workbench_scan_result: dict | None = None
_workbench_type_overrides: dict[str, str] = {}


def refresh_override_table(paper_file):
    """刷新低置信度段落列表，供用户手动修正类型。"""
    global _workbench_scan_result, _workbench_type_overrides
    if paper_file is None:
        return [], "请先上传论文"
    try:
        inventory = scan_document(paper_file.name)
        _workbench_scan_result = inventory
        _workbench_type_overrides = {}  # 重置修正
    except Exception as exc:
        return [], f"扫描失败：{exc}"

    confidence_items = inventory.get("confidence", [])
    low_items = [item for item in confidence_items if item.get("confidence") == "low"]

    if not low_items:
        return [], "未发现低置信度段落，所有识别结果置信度较高"

    # 构建表格数据
    rows = []
    for item in low_items:
        element = item.get("element", "")
        reason = item.get("reason", "")
        samples = item.get("samples", [])
        sample_text = samples[0].get("text", "")[:30] if samples else ""
        rows.append([element, "low", f"{reason} (样例: {sample_text})", ""])

    return rows, f"发现 {len(low_items)} 个低置信度段落，请在'修正为'列选择目标类型"


def preview_correction_plan(
    paper_file, sample_file, template_choice, body_font, body_size, body_spacing,
    body_indent, heading_font, heading1_size, heading2_size, heading3_size,
    table_style, table_font_size, image_max_width, language="auto",
):
    """Dry-run: show what would be modified without applying changes."""
    if paper_file is None:
        return "请先上传 .docx 论文。"
    try:
        from .application.style_workbench import build_correction_plan
        c = PaperFormatCorrector(config_path)
        c.config = c._merge_config(c.config, _load_workbench_template(template_choice))
        if sample_file:
            c.config = c._merge_config(c.config, learn_style_profile(sample_file.name))
        c.config = c._merge_config(c.config, manual_style_config(
            body_font, body_size, body_spacing, body_indent, heading1_size,
            heading2_size, heading3_size, heading_font, table_style,
            table_font_size, image_max_width, language=language,
        ))
        plan = build_correction_plan(paper_file.name, c.config.get("format_rules", {}))
        lines = [
            f"═══ 矫正计划（影响 {plan.total_affected} 个元素）═══\n",
            "元素类型          数量    操作                            来源",
            "─" * 70,
        ]
        for item in plan.items:
            lines.append(
                f"  {item.element_type:<12}  {item.element_count:>4}    "
                f"{item.action:<30}  [{item.source}]"
            )
        if plan.risk_items:
            lines.append(f"\n⚠ 需要人工确认 ({len(plan.risk_items)} 项):")
            for risk in plan.risk_items:
                lines.append(f"  - {risk.get('element', '')}: {risk.get('reason', '')}")
        return "\n".join(lines)
    except Exception as exc:
        return f"生成计划失败：{exc}"


def inspect_sample_style(sample_file):
    if sample_file is None:
        return "请上传一份已排好版的 .docx 样本文档。"
    try:
        return json.dumps(explain_style_profile(sample_file.name), ensure_ascii=False, indent=2, default=str)
    except Exception as exc:
        return f"样式学习失败：{exc}"


def save_sample_template(sample_file, name, category):
    """Save a learned sample profile as a reusable local database template."""
    if sample_file is None:
        return "请先上传已排好版的 .docx 样本文档。", gr.update()
    try:
        profile = learn_style_profile(sample_file.name)
        record = _template_repository().save_personal_template(
            name or Path(sample_file.name).stem, category, profile, "由样本文档自动学习",
        )
        return f"已保存个人模板：{record.name}", gr.update(choices=workbench_template_choices())
    except Exception as exc:
        return f"保存模板失败：{exc}", gr.update()


def save_requirement_as_template(requirement_file, name):
    """Parse a requirement doc and save the result as a reusable template."""
    if requirement_file is None:
        return "请先上传格式要求文档（.txt/.md/.docx）", gr.update()
    try:
        from .domain.document.requirement_parser import RequirementParser
        parser = RequirementParser()
        req_config = parser.parse(requirement_file.name)
        tpl_name = name.strip() if name and name.strip() else Path(requirement_file.name).stem
        record = _template_repository().save_personal_template(
            tpl_name, "导入模板", req_config, f"从需求文档 {Path(requirement_file.name).name} 导入",
        )
        return f"已从需求文档生成并保存模板：{record.name}", gr.update(choices=workbench_template_choices())
    except Exception as exc:
        return f"保存需求模板失败：{exc}", gr.update()


def process_with_workbench(  # noqa: PLR0913
    paper_file, sample_file, template_choice, body_font, body_size, body_spacing,
    body_indent, heading_font, heading1_size, heading2_size, heading3_size,
    table_style, table_font_size, image_max_width, language="auto",
):
    """Apply a preset, an optional learned sample and explicit UI settings."""
    global _workbench_type_overrides
    if paper_file is None:
        return None, "请上传论文文件", None
    if Path(paper_file.name).suffix.lower() != ".docx":
        return None, "格式工作台当前只处理 .docx 文件", None
    if sample_file and Path(sample_file.name).suffix.lower() != ".docx":
        return None, "样本文档必须是 .docx 文件", None

    try:
        c = PaperFormatCorrector(config_path)
        c.config = c._merge_config(c.config, _load_workbench_template(template_choice))
        if sample_file:
            c.config = c._merge_config(c.config, learn_style_profile(sample_file.name))
        c.config = c._merge_config(c.config, manual_style_config(
            body_font, body_size, body_spacing, body_indent, heading1_size,
            heading2_size, heading3_size, heading_font, table_style,
            table_font_size, image_max_width, language=language,
        ))
        # 使用用户手动修正的段落类型
        type_overrides = _workbench_type_overrides if _workbench_type_overrides else None
        c.corrector = FormatCorrector(c.template_path, c.config, type_overrides=type_overrides)
    except Exception as exc:
        return None, f"无法生成格式方案：{exc}", None

    output_dir = Path(tempfile.mkdtemp())
    _temp_dirs.append(str(output_dir))
    output_path = output_dir / f"workbench_{Path(paper_file.name).name}"
    try:
        report = c.corrector.correct_document(paper_file.name, str(output_path))
        diff_path = output_path.with_suffix(".diff.html")
        DiffReporter().generate_html_report(paper_file.name, str(output_path), str(diff_path))
    except Exception as exc:
        return None, f"应用格式失败：{exc}", None

    source = "已学习样本文档；" if sample_file else ""
    coverage = build_application_report(paper_file.name, report)
    summary = source + format_report_text(report)
    summary += "\n\n覆盖与待复核项：\n" + json.dumps(coverage, ensure_ascii=False, indent=2)
    return str(output_path), summary, str(diff_path)


def process_batch_files(files, template_choice):
    """Process multiple files in batch with zip download and summary report."""
    if not files:
        return None, "请先选择要处理的文件"
    from .application.batch_service import BatchCorrectionService
    merged_config = _load_workbench_template(template_choice)
    merged_config.update({"format_rules": config.get("format_rules", {})})
    try:
        c = PaperFormatCorrector(config_path)
        c.config = c._merge_config(c.config, merged_config)
    except Exception:
        c = PaperFormatCorrector(config_path)

    service = BatchCorrectionService(c.config)
    input_paths = [f.name for f in files]
    output_dir = Path(tempfile.mkdtemp())
    _temp_dirs.append(str(output_dir))

    summary = service.process_files(
        input_paths, output_dir, score=True,
        progress_callback=lambda cur, total, name: None,
    )

    # 创建 zip 压缩包
    zip_path = output_dir / "batch_results.zip"
    summary.create_zip(zip_path)

    return str(zip_path), summary.generate_report(fmt="text")


def generate_cover(title, title_en, author, college, major, student_id, advisor, date, university, paper_type, template):
    """生成封面"""
    if not title:
        return None, "请填写论文题目"

    metadata = {
        "title": title,
        "title_en": title_en,
        "author": author,
        "college": college,
        "major": major,
        "student_id": student_id,
        "advisor": advisor,
        "date": date,
        "university": university,
        "paper_type": paper_type,
    }

    output_dir = Path(tempfile.mkdtemp())
    _temp_dirs.append(str(output_dir))
    output_path = output_dir / "cover.docx"

    generator = CoverPageGenerator()
    generator.generate(metadata, str(output_path), template)

    return str(output_path), "封面生成成功！"


# ---------- 模板库管理 ----------

_template_repo = None


def _get_template_repo() -> TemplateRepository:
    global _template_repo
    if _template_repo is None:
        _template_repo = TemplateRepository()
    return _template_repo


def template_list(category=None):
    """列出模板库中的模板"""
    repo = _get_template_repo()
    templates = repo.list_templates(category=category if category and category != "全部" else None)
    if not templates:
        return "模板库为空"
    lines = []
    for t in templates:
        tags_str = f" [{', '.join(t.tags)}]" if t.tags else ""
        org_str = f" - {t.organization}" if t.organization else ""
        status = "✓" if t.is_active else "✗"
        lines.append(f"{status} **{t.name}** ({t.category}){org_str}{tags_str} v{t.version} [{t.source}]")
    return "\n".join(lines)


def template_search(keyword):
    """搜索模板"""
    if not keyword or not keyword.strip():
        return "请输入搜索关键词"
    repo = _get_template_repo()
    templates = repo.search_templates(keyword.strip())
    if not templates:
        return f"未找到匹配 '{keyword}' 的模板"
    lines = []
    for t in templates:
        lines.append(f"**{t.name}** ({t.category}) - {t.description[:50]}")
    return "\n".join(lines)


def template_detail(slug):
    """查看模板详情"""
    if not slug or not slug.strip():
        return "请输入模板 slug"
    repo = _get_template_repo()
    record = repo.get(slug.strip())
    if record is None:
        return f"模板不存在: {slug}"
    tags_str = ", ".join(record.tags) if record.tags else "无"
    versions = repo.get_versions(record.slug)
    version_info = "\n".join([f"  v{v['version']} ({v['created_at']}): {v['changelog']}" for v in versions[:5]])
    return f"""模板详情:
名称: {record.name}
分类: {record.category}
来源: {record.source}
组织: {record.organization or '未指定'}
学历层次: {record.degree_level or '未指定'}
学科: {record.discipline or '未指定'}
语言: {record.language}
版本: {record.version}
标签: {tags_str}
说明: {record.description or '无'}
创建时间: {record.created_at}
更新时间: {record.updated_at}

版本历史:
{version_info or '  无版本记录'}"""


def template_delete(slug):
    """删除模板"""
    if not slug or not slug.strip():
        return "请输入模板 slug"
    repo = _get_template_repo()
    success = repo.delete_template(slug.strip())
    if success:
        return f"模板 {slug} 已删除"
    return f"模板不存在: {slug}"


def template_check_update():
    """检查云端模板更新"""
    import yaml as _yaml

    config_path = Path("config/updater.yaml")
    remote_url = ""
    if config_path.exists():
        try:
            with open(config_path, encoding="utf-8") as f:
                updater_config = _yaml.safe_load(f) or {}
            remote_url = updater_config.get("updater", {}).get("remote_url", "")
        except Exception:
            pass

    if not remote_url:
        return "未配置远程仓库地址，请在 config/updater.yaml 中设置 remote_url"

    try:
        from .infrastructure.updater import AutoUpdater, VersionChecker

        repo = _get_template_repo()
        checker = VersionChecker(remote_url)

        local_versions = {}
        for t in repo.list_templates(active_only=False):
            template_id = t.slug
            for prefix in ("remote-", "personal-", "builtin-"):
                if template_id.startswith(prefix):
                    template_id = template_id[len(prefix):]
                    break
            local_versions[template_id] = t.version

        updates = checker.check_updates(local_versions)

        if not updates:
            return "所有模板已是最新。"

        lines = [f"发现 {len(updates)} 个更新:"]
        for u in updates:
            if u["action"] == "new":
                lines.append(f"  + {u['name']} (新模板 v{u['version']})")
            else:
                lines.append(f"  ~ {u['name']} {u['from_version']} -> {u['to_version']}")

        updater = AutoUpdater(repo, checker)
        applied = updater.check_now()
        lines.append(f"\n已更新 {len(applied)} 个模板。")
        return "\n".join(lines)

    except Exception as e:
        return f"检查更新失败（网络不可用或地址错误）: {e}\n已降级为跳过，不影响本地模板使用。"


def template_export(slug, fmt):
    """导出模板"""
    if not slug or not slug.strip():
        return None, "请输入模板 slug"
    repo = _get_template_repo()
    output_dir = Path(tempfile.mkdtemp())
    _temp_dirs.append(str(output_dir))
    output_path = output_dir / f"template_{slug.strip()}.{fmt}"
    try:
        if fmt == "yaml":
            repo.export_to_yaml(slug.strip(), str(output_path))
        else:
            repo.export_to_json(slug.strip(), str(output_path))
        return str(output_path), f"导出成功: {output_path.name}"
    except Exception as e:
        return None, f"导出失败: {e}"


def template_import(file, name, category):
    """导入模板"""
    if file is None:
        return "请上传模板文件"
    if not name or not name.strip():
        return "请输入模板名称"
    repo = _get_template_repo()
    try:
        path = file.name
        if path.endswith((".yaml", ".yml")):
            record = repo.import_from_yaml(path)
        elif path.endswith(".json"):
            record = repo.import_from_json(path)
        else:
            return "仅支持 YAML 和 JSON 格式"
        return f"导入成功: {record.name} (slug: {record.slug})"
    except Exception as e:
        return f"导入失败: {e}"


def history_list():
    """列出处理历史"""
    try:
        records = _get_template_repo().list_processing_history(limit=50)
        if not records:
            return "暂无处理记录"
        lines = ["ID  输入文件                              状态  评分    耗时    处理时间", "─" * 80]
        for r in records:
            score = f"{r['quality_score']:.1f}" if r["quality_score"] else "-"
            elapsed = f"{r['processing_time']:.1f}s" if r["processing_time"] else "-"
            created = r["created_at"][:19] if r["created_at"] else ""
            lines.append(f"{r['id']:<4}{Path(r['input_file']).name:<38}{r['status']:<6}{score:<8}{elapsed:<8}{created}")
        return "\n".join(lines)
    except Exception as exc:
        return f"加载历史失败: {exc}"


def history_detail(record_id):
    """获取单条历史详情"""
    if not record_id or record_id <= 0:
        return "请输入有效的记录 ID"
    try:
        record = _get_template_repo().get_processing_history(int(record_id))
        if not record:
            return f"记录不存在: {record_id}"
        lines = [
            f"记录 ID: {record['id']}",
            f"输入文件: {record['input_file']}",
            f"输出文件: {record['output_file']}",
            f"模板: {record.get('template_used', '默认')}",
            f"质量评分: {record['quality_score']:.1f}",
            f"总元素: {record['total_elements']}  已修改: {record['modified_elements']}",
            f"耗时: {record['processing_time']:.1f}s",
            f"状态: {record['status']}",
            f"处理时间: {record['created_at']}",
            "",
            "─── 详细报告 ───",
            json.dumps(record.get("report", {}), ensure_ascii=False, indent=2, default=str),
        ]
        return "\n".join(lines)
    except Exception as exc:
        return f"加载详情失败: {exc}"


def history_delete(record_id):
    """删除单条历史"""
    if not record_id or record_id <= 0:
        return "请输入有效的记录 ID"
    try:
        success = _get_template_repo().delete_processing_history(int(record_id))
        if success:
            return f"记录 {int(record_id)} 已删除"
        return f"记录不存在: {int(record_id)}"
    except Exception as exc:
        return f"删除失败: {exc}"


def check_rules(paper_file, rules_file):
    """自定义规则检查"""
    if paper_file is None:
        return "请上传论文文件"
    if rules_file is None:
        return "请上传规则文件 (YAML)"

    # 格式转换（如果需要）
    input_path = paper_file.name
    converter = FileConverter()
    if converter.needs_conversion(input_path):
        try:
            output_dir = Path(tempfile.mkdtemp())
            _temp_dirs.append(str(output_dir))
            input_path = converter.convert(input_path, str(output_dir))
        except Exception as e:
            return f"文件格式转换失败: {e}"

    c = PaperFormatCorrector(config_path)
    from .infrastructure.path_security import validate_input_path
    rules_path = str(validate_input_path(rules_file.name, {".yaml", ".yml"}))
    results = c.check_rules(input_path, rules_path=rules_path)
    return c.rule_engine.format_report(results)


def find_free_port(start=7860, end=7900):
    """查找可用端口"""
    import socket
    for port in range(start, end):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return start


# ---------- AI 文档生成（对话式） ----------

def _get_or_create_ai_session(
    session_id: str,
    provider: str,
    api_key: str,
    model: str,
) -> Any:
    """获取或创建AI文档生成器会话"""
    from .domain.document.ai_doc_generator import AIDocGenerator

    # 限制 session 数量，防止内存泄漏
    if len(_ai_sessions) >= _MAX_SESSIONS:
        oldest_key = next(iter(_ai_sessions))
        del _ai_sessions[oldest_key]

    if session_id not in _ai_sessions:
        _ai_sessions[session_id] = {
            "generator": AIDocGenerator(
                provider=provider,
                api_key=api_key or None,
                model=model or None,
            ),
            "structure": None,
            "outline_confirmed": False,
        }

    session = _ai_sessions[session_id]
    gen = session["generator"]

    # 更新配置
    gen.provider = provider
    gen.api_key = api_key or gen._get_default_key()
    if model:
        gen.model = model

    return gen


def ai_chat_send(
    message: str,
    chat_history: list,
    session_id: str,
    provider: str,
    api_key: str,
    model: str,
    doc_type: str,
):
    """处理用户发送的消息（非流式）

    工作流程：
    1. 如果是首次对话，生成大纲
    2. 如果用户确认大纲，开始逐节生成
    3. 如果用户要求修改，执行修改
    """
    if not message or not message.strip():
        return chat_history, "", "请输入消息"

    gen = _get_or_create_ai_session(session_id, provider, api_key, model)
    chat_history = chat_history or []

    user_msg = message.strip()
    chat_history.append({"role": "user", "content": user_msg})

    try:
        # 检查是否需要生成大纲
        if gen.session.outline is None:
            # 首次对话，生成大纲
            outline = gen.generate_outline(user_msg, doc_type or "通用文档")

            # 格式化大纲显示
            outline_text = f"**识别的文档类型**: {outline.get('doc_type', '未知')}\n\n"
            outline_text += f"**文档标题**: {outline.get('title', '未知')}\n\n"
            outline_text += f"**摘要**: {outline.get('abstract', '')}\n\n"
            outline_text += "**大纲结构**:\n\n"

            for _i, item in enumerate(outline.get("outline", [])):
                item_type = item.get("type", "")
                title = item.get("title", "")
                desc = item.get("description", "")
                indent = "  " if "2" in item_type or "3" in item_type else ""
                outline_text += f"{indent}{title}\n"
                if desc:
                    outline_text += f"{indent}  _{desc}_\n"

            outline_text += "\n请确认大纲是否满意，或告诉我需要修改的地方。\n"
            outline_text += "回复 **确认** 开始生成内容，或告诉我需要调整的地方。"

            chat_history.append({"role": "assistant", "content": outline_text})
            status = "大纲已生成，请确认或修改"

        elif not gen.session.outline.get("structure"):
            # 大纲已生成但未确认，检查用户是否确认
            if "确认" in user_msg or "ok" in user_msg.lower() or "开始" in user_msg:
                gen.confirm_outline(True)
                chat_history.append({"role": "assistant", "content": "大纲已确认，开始生成文档内容...\n\n请稍候，正在逐节生成..."})

                # 生成完整文档
                structure = gen.generate_structure(
                    gen.session.outline.get("title", ""),
                    gen.session.doc_type or "通用文档",
                )
                gen.session.outline["structure"] = structure

                # 生成预览
                doc_gen = DocGenerator()
                preview = doc_gen.generate_preview(structure)

                preview_msg = "**文档预览**:\n\n" + preview + "\n\n文档已生成完成！点击下方按钮导出。"
                chat_history.append({"role": "assistant", "content": preview_msg})
                status = "文档生成完成，可以导出"
            else:
                # 用户要求修改大纲
                chat_history.append({"role": "assistant", "content": f"收到修改意见：{user_msg}\n\n请告诉我具体需要调整的内容，或者回复 **确认** 使用当前大纲。"})
                status = "等待确认或修改"

        else:
            # 文档已生成，处理后续对话
            chat_history.append({"role": "assistant", "content": "文档已生成完成。\n\n你可以：\n1. 点击 **导出docx** 按钮下载文档\n2. 告诉我需要修改的内容，我会帮你调整\n3. 回复 **重新开始** 生成新文档"})
            status = "文档已就绪"

    except Exception:
        logging.getLogger(__name__).exception("AI处理失败")
        chat_history.append({"role": "assistant", "content": "出错了: 请检查API配置后重试。"})
        status = "错误"

    return chat_history, "", status


def ai_chat_send_stream(  # noqa: C901
    message: str,
    chat_history: list,
    session_id: str,
    provider: str,
    api_key: str,
    model: str,
    doc_type: str,
):
    """处理用户发送的消息（流式输出）"""
    if not message or not message.strip():
        yield chat_history, "", "请输入消息"
        return

    gen = _get_or_create_ai_session(session_id, provider, api_key, model)
    chat_history = chat_history or []

    user_msg = message.strip()
    chat_history.append({"role": "user", "content": user_msg})

    # 检查是否需要生成大纲
    if gen.session.outline is None:
        # 首次对话，流式生成大纲
        chat_history.append({"role": "assistant", "content": ""})
        current_content = ""

        for chunk in gen.generate_outline_stream(user_msg, doc_type or "通用文档"):
            current_content += chunk
            chat_history[-1]["content"] = current_content
            yield chat_history, "", "正在生成大纲..."

        # 解析大纲并格式化
        try:
            outline = gen.session.outline
            outline_text = f"**识别的文档类型**: {outline.get('doc_type', '未知')}\n\n"
            outline_text += f"**文档标题**: {outline.get('title', '未知')}\n\n"
            outline_text += f"**摘要**: {outline.get('abstract', '')}\n\n"
            outline_text += "**大纲结构**:\n\n"

            for item in outline.get("outline", []):
                item_type = item.get("type", "")
                title = item.get("title", "")
                desc = item.get("description", "")
                indent = "  " if "2" in item_type or "3" in item_type else ""
                outline_text += f"{indent}{title}\n"
                if desc:
                    outline_text += f"{indent}  _{desc}_\n"

            outline_text += "\n请确认大纲是否满意，或告诉我需要修改的地方。\n"
            outline_text += "回复 **确认** 开始生成内容，或告诉我需要调整的地方。"

            chat_history[-1]["content"] = outline_text
        except Exception:
            pass

        yield chat_history, "", "大纲已生成，请确认"

    elif not gen.session.outline.get("structure"):
        # 大纲已生成但未确认
        if "确认" in user_msg or "ok" in user_msg.lower() or "开始" in user_msg:
            gen.confirm_outline(True)
            chat_history.append({"role": "assistant", "content": "大纲已确认，开始生成文档内容..."})
            yield chat_history, "", "正在生成文档..."

            # 流式生成完整文档
            structure = None
            for event in gen.generate_all_sections_stream():
                if event.get("type") == "start":
                    section_title = event.get("section_title", "")
                    chat_history[-1]["content"] = f"正在生成: {section_title}..."
                    yield chat_history, "", f"生成中: {section_title}"
                elif event.get("type") == "chunk":
                    pass  # 流式内容在内部累积
                elif event.get("type") == "all_done":
                    structure = event.get("structure")

            if structure:
                gen.session.outline["structure"] = structure
                doc_gen = DocGenerator()
                preview = doc_gen.generate_preview(structure)
                preview_msg = "**文档预览**:\n\n" + preview + "\n\n文档已生成完成！点击下方按钮导出。"
                chat_history.append({"role": "assistant", "content": preview_msg})
                yield chat_history, "", "文档生成完成"
            else:
                chat_history.append({"role": "assistant", "content": "文档生成失败，请重试。"})
                yield chat_history, "", "生成失败"
        else:
            # 用户要求修改大纲
            chat_history.append({"role": "assistant", "content": f"收到修改意见：{user_msg}\n\n请告诉我具体需要调整的内容，或者回复 **确认** 使用当前大纲。"})
            yield chat_history, "", "等待确认或修改"

    else:
        # 文档已生成，处理后续对话
        chat_history.append({"role": "assistant", "content": "文档已生成完成。\n\n你可以：\n1. 点击 **导出docx** 按钮下载文档\n2. 告诉我需要修改的内容\n3. 回复 **重新开始** 生成新文档"})
        yield chat_history, "", "文档已就绪"


def ai_export_docx(session_id: str):
    """导出文档为docx"""
    if session_id not in _ai_sessions:
        return None, "没有进行中的文档生成会话"

    session = _ai_sessions[session_id]
    structure = session.get("structure") or (
        session["generator"].session.outline.get("structure")
        if session["generator"].session.outline
        else None
    )

    if not structure:
        return None, "文档尚未生成完成"

    output_dir = Path(tempfile.mkdtemp())
    _temp_dirs.append(str(output_dir))
    output_path = output_dir / "generated_document.docx"

    doc_gen = DocGenerator()
    doc_gen.generate(structure, str(output_path))

    return str(output_path), f"导出成功！文件大小: {output_path.stat().st_size / 1024:.1f} KB"


def ai_reset_session(session_id: str):
    """重置AI会话"""
    if session_id in _ai_sessions:
        _ai_sessions[session_id]["generator"].reset_session()
        _ai_sessions[session_id]["structure"] = None
        _ai_sessions[session_id]["outline_confirmed"] = False
    return [], "", "会话已重置，可以开始新的文档生成"


def build_ui():
    """构建界面"""
    with gr.Blocks(title="论文格式矫正工具", theme=gr.themes.Soft()) as app:
        gr.Markdown("# 论文格式自动矫正工具 v3.0")
        gr.Markdown("上传论文和格式要求，一键矫正论文格式")

        # 存储当前会话ID
        session_state = gr.State(value="default_session")

        with gr.Tabs():
            # Tab 1: 论文矫正
            with gr.Tab("论文矫正"):
                with gr.Row():
                    with gr.Column(scale=1):
                        paper_input = gr.File(label="上传论文 (.docx/.doc/.odt/.rtf/.pdf/.txt/.md)", file_types=[".docx", ".doc", ".odt", ".rtf", ".pdf", ".txt", ".md", ".markdown"])

                        # 格式预设选择
                        preset_options = ["无 (使用默认配置)"]
                        for p in list_presets():
                            preset_options.append(f"{p['name']} - {p['description']}")
                        preset_dropdown = gr.Dropdown(
                            choices=preset_options,
                            value="无 (使用默认配置)",
                            label="格式预设 (IEEE/Nature/Science/APA/毕业论文)",
                        )

                        template_input = gr.File(label="模板文件 (可选, .docx)", file_types=[".docx"])
                        requirement_input = gr.File(label="格式要求文档 (可选, .txt/.md/.docx/.pdf)", file_types=[".txt", ".md", ".docx", ".pdf"])
                        config_input = gr.File(label="自定义配置 (可选, .yaml)", file_types=[".yaml", ".yml"])

                        with gr.Row():
                            do_score = gr.Checkbox(label="输出质量评分", value=True)
                            do_diff = gr.Checkbox(label="生成对比报告", value=True)

                        export_checkboxes = gr.CheckboxGroup(
                            choices=["pdf", "html", "txt", "md"],
                            label="额外导出格式",
                        )

                        process_btn = gr.Button("开始矫正", variant="primary", size="lg")

                    with gr.Column(scale=2):
                        output_file = gr.File(label="矫正结果下载")
                        score_output = gr.Textbox(label="质量评分报告", lines=15, max_lines=20)
                        report_output = gr.Textbox(label="处理报告", lines=10, max_lines=15)
                        diff_output = gr.File(label="对比报告下载 (HTML)")

                process_btn.click(
                    fn=process_paper,
                    inputs=[paper_input, requirement_input, config_input, template_input, preset_dropdown, export_checkboxes, do_score, do_diff],
                    outputs=[output_file, score_output, report_output, diff_output],
                )

            with gr.Tab("格式工作台"):
                gr.Markdown("上传论文后先扫描元素；可套用期刊/院校预设、学习一份已排好版的样本文档，再对正文、标题、表格和图片全局应用。")
                with gr.Row():
                    with gr.Column():
                        wb_paper = gr.File(label="待处理论文 (.docx)", file_types=[".docx"])
                        wb_sample = gr.File(label="样本文档（可选，已排好版 .docx）", file_types=[".docx"])
                        wb_template = gr.Dropdown(choices=workbench_template_choices(), value="无（使用默认配置）", label="模板库（期刊 / 高校 / 我的模板）")
                        scan_btn = gr.Button("扫描文档元素")
                        plan_btn = gr.Button("预览矫正计划（不应用）")
                        sample_btn = gr.Button("查看样本文档学习结果")
                        with gr.Row():
                            wb_template_name = gr.Textbox(label="保存为我的模板", placeholder="例如：张同学硕士论文")
                            wb_template_category = gr.Dropdown(["高校毕业论文", "国际期刊与会议", "引用与写作规范", "个人"], value="高校毕业论文", label="模板分类")
                        save_template_btn = gr.Button("将样本文档保存到模板库")
                        wb_req_file = gr.File(label="格式要求文档（可选，用于保存为模板）", file_types=[".txt", ".md", ".docx", ".pdf"])
                        save_req_btn = gr.Button("将需求文档保存为模板")
                        with gr.Accordion("语言与字体", open=True):
                            wb_language = gr.Dropdown(
                                choices=["auto", "chinese", "english", "japanese", "korean"],
                                value="auto", label="文档语言",
                                info="选择文档主要语言，将自动填充对应字体。'auto' 根据内容自动检测。",
                            )
                            wb_font_preview = gr.Textbox(
                                label="字体预览", lines=5, interactive=False,
                                value=update_font_preview("auto"),
                            )
                        with gr.Accordion("正文与标题", open=True):
                            wb_body_font = gr.Textbox(label="正文字体", value="宋体")
                            wb_body_size = gr.Number(label="正文字号 (pt)", value=12, precision=1)
                            wb_body_spacing = gr.Number(label="正文行距（倍数）", value=1.5, precision=2)
                            wb_body_indent = gr.Number(label="正文首行缩进（字符）", value=2, precision=1)
                            wb_heading_font = gr.Textbox(label="标题字体", value="黑体")
                            with gr.Row():
                                wb_heading1 = gr.Number(label="一级标题 (pt)", value=16, precision=1)
                                wb_heading2 = gr.Number(label="二级标题 (pt)", value=14, precision=1)
                                wb_heading3 = gr.Number(label="三级标题 (pt)", value=12, precision=1)
                        with gr.Accordion("表格与图片", open=False):
                            wb_table_style = gr.Radio(["three_line", "full_border", "keep"], value="three_line", label="表格样式")
                            wb_table_size = gr.Number(label="表格字号 (pt)", value=10.5, precision=1)
                            wb_image_width = gr.Dropdown(["full", "90%", "80%", "70%", "50%"], value="full", label="图片最大宽度")
                        with gr.Accordion("低置信度段落修正（可选）", open=False):
                            gr.Markdown("扫描后若发现低置信度段落，可在此手动修正类型。")
                            wb_override_table = gr.Dataframe(
                                headers=["段落类型", "置信度", "原因", "修正为"],
                                datatype=["str", "str", "str", "str"],
                                interactive=False,
                                label="低置信度段落",
                                wrap=True,
                            )
                            wb_override_btn = gr.Button("刷新低置信度列表")
                            wb_override_status = gr.Textbox(label="修正状态", lines=2, interactive=False)
                        wb_apply = gr.Button("应用到全部同类元素", variant="primary", size="lg")
                    with gr.Column():
                        wb_inventory = gr.Code(label="扫描结果（元素数量、样例和风险）", language="json", lines=22)
                        wb_output = gr.File(label="格式工作台输出")
                        wb_report = gr.Textbox(label="应用报告", lines=12)
                        wb_diff = gr.File(label="差异报告（HTML）")

                scan_btn.click(fn=scan_workbench_document, inputs=[wb_paper], outputs=[wb_inventory])
                wb_override_btn.click(fn=refresh_override_table, inputs=[wb_paper], outputs=[wb_override_table, wb_override_status])

                # Language selection triggers font preview update
                wb_language.change(
                    fn=update_font_preview,
                    inputs=[wb_language],
                    outputs=[wb_font_preview],
                )

                plan_btn.click(
                    fn=preview_correction_plan,
                    inputs=[wb_paper, wb_sample, wb_template, wb_body_font, wb_body_size, wb_body_spacing,
                            wb_body_indent, wb_heading_font, wb_heading1, wb_heading2, wb_heading3,
                            wb_table_style, wb_table_size, wb_image_width, wb_language],
                    outputs=[wb_inventory],
                )
                sample_btn.click(fn=inspect_sample_style, inputs=[wb_sample], outputs=[wb_inventory])
                save_template_btn.click(
                    fn=save_sample_template,
                    inputs=[wb_sample, wb_template_name, wb_template_category],
                    outputs=[wb_report, wb_template],
                )
                save_req_btn.click(
                    fn=save_requirement_as_template,
                    inputs=[wb_req_file, wb_template_name],
                    outputs=[wb_report, wb_template],
                )
                wb_apply.click(
                    fn=process_with_workbench,
                    inputs=[wb_paper, wb_sample, wb_template, wb_body_font, wb_body_size, wb_body_spacing,
                            wb_body_indent, wb_heading_font, wb_heading1, wb_heading2, wb_heading3,
                            wb_table_style, wb_table_size, wb_image_width, wb_language],
                    outputs=[wb_output, wb_report, wb_diff],
                )

            # Tab: 模板库管理
            with gr.Tab("模板库管理"):
                gr.Markdown("### 模板库 - 搜索、查看、导入、导出模板")
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("#### 模板列表")
                        tm_category = gr.Dropdown(
                            choices=["全部", "高校毕业论文", "国际期刊与会议", "引用与写作规范", "个人"],
                            value="全部", label="按分类筛选",
                        )
                        tm_list_btn = gr.Button("刷新列表")
                        tm_list_output = gr.Textbox(label="模板列表", lines=15, max_lines=20)

                        gr.Markdown("#### 搜索模板")
                        tm_search_input = gr.Textbox(label="搜索关键词", placeholder="输入学校、期刊、关键词...")
                        tm_search_btn = gr.Button("搜索")
                        tm_search_output = gr.Textbox(label="搜索结果", lines=8)

                    with gr.Column(scale=1):
                        gr.Markdown("#### 模板详情")
                        tm_slug_input = gr.Textbox(label="模板 Slug", placeholder="例如: builtin-ieee")
                        tm_detail_btn = gr.Button("查看详情")
                        tm_detail_output = gr.Textbox(label="详情", lines=15, max_lines=20)

                        gr.Markdown("#### 导入/导出")
                        with gr.Row():
                            tm_import_file = gr.File(label="上传模板 (.yaml/.json)", file_types=[".yaml", ".yml", ".json"])
                        tm_import_name = gr.Textbox(label="模板名称", placeholder="新模板名称")
                        tm_import_category = gr.Dropdown(
                            ["高校毕业论文", "国际期刊与会议", "引用与写作规范", "个人"],
                            value="个人", label="分类",
                        )
                        tm_import_btn = gr.Button("导入模板")
                        tm_import_output = gr.Textbox(label="导入结果", lines=2)

                        with gr.Row():
                            tm_export_slug = gr.Textbox(label="导出 Slug", placeholder="模板 slug")
                            tm_export_fmt = gr.Dropdown(["yaml", "json"], value="yaml", label="格式")
                        tm_export_btn = gr.Button("导出模板")
                        tm_export_file = gr.File(label="导出文件")
                        tm_export_output = gr.Textbox(label="导出结果", lines=2)

                        gr.Markdown("#### 删除模板")
                        tm_delete_slug = gr.Textbox(label="删除 Slug", placeholder="个人模板 slug")
                        tm_delete_btn = gr.Button("删除", variant="stop")
                        tm_delete_output = gr.Textbox(label="删除结果", lines=2)

                        gr.Markdown("#### 云端更新")
                        tm_update_btn = gr.Button("检查模板更新", variant="secondary")
                        tm_update_output = gr.Textbox(label="更新结果", lines=3)

                tm_list_btn.click(fn=template_list, inputs=[tm_category], outputs=[tm_list_output])
                tm_search_btn.click(fn=template_search, inputs=[tm_search_input], outputs=[tm_search_output])
                tm_detail_btn.click(fn=template_detail, inputs=[tm_slug_input], outputs=[tm_detail_output])
                tm_import_btn.click(fn=template_import, inputs=[tm_import_file, tm_import_name, tm_import_category], outputs=[tm_import_output])
                tm_export_btn.click(fn=template_export, inputs=[tm_export_slug, tm_export_fmt], outputs=[tm_export_file, tm_export_output])
                tm_delete_btn.click(fn=template_delete, inputs=[tm_delete_slug], outputs=[tm_delete_output])
                tm_update_btn.click(fn=template_check_update, inputs=[], outputs=[tm_update_output])

            # Tab: 报告中心
            with gr.Tab("报告中心"):
                gr.Markdown("### 历史处理记录 - 查看、下载、删除")
                with gr.Row():
                    with gr.Column(scale=1):
                        hist_refresh_btn = gr.Button("刷新列表")
                        hist_list = gr.Textbox(label="处理记录", lines=20, max_lines=25)
                        with gr.Row():
                            hist_id = gr.Number(label="记录 ID", value=0, precision=0)
                            hist_detail_btn = gr.Button("查看详情")
                            hist_delete_btn = gr.Button("删除记录", variant="stop")
                        hist_status = gr.Textbox(label="操作结果", lines=2)
                    with gr.Column(scale=2):
                        hist_detail = gr.Textbox(label="详细报告", lines=25, max_lines=30)

                hist_refresh_btn.click(fn=history_list, inputs=[], outputs=[hist_list])
                hist_detail_btn.click(fn=history_detail, inputs=[hist_id], outputs=[hist_detail])
                hist_delete_btn.click(fn=history_delete, inputs=[hist_id], outputs=[hist_status])

            # Tab: 批量处理
            with gr.Tab("批量处理"):
                gr.Markdown("### 批量矫正 - 选择多个文件一次性处理")
                with gr.Row():
                    with gr.Column(scale=1):
                        batch_files = gr.File(label="选择多个论文文件", file_count="multiple", file_types=[".docx", ".doc", ".odt", ".rtf", ".pdf", ".txt", ".md"])
                        batch_template = gr.Dropdown(choices=workbench_template_choices(), value="无（使用默认配置）", label="模板库")
                        batch_btn = gr.Button("开始批量处理", variant="primary", size="lg")
                    with gr.Column(scale=2):
                        batch_output = gr.File(label="批量处理结果下载 (ZIP)")
                        batch_result = gr.Textbox(label="批量处理结果", lines=20, max_lines=25)

                batch_btn.click(fn=process_batch_files, inputs=[batch_files, batch_template], outputs=[batch_output, batch_result])

            # Tab: 封面生成
            with gr.Tab("封面生成"):
                with gr.Row():
                    with gr.Column():
                        cover_title = gr.Textbox(label="论文题目", placeholder="基于深度学习的...")
                        cover_title_en = gr.Textbox(label="英文题目 (可选)", placeholder="Research on...")
                        cover_author = gr.Textbox(label="作者姓名", placeholder="张三")
                        cover_college = gr.Textbox(label="学院", placeholder="计算机科学与技术学院")
                        cover_major = gr.Textbox(label="专业", placeholder="计算机科学与技术")
                        cover_id = gr.Textbox(label="学号 (可选)")
                        cover_advisor = gr.Textbox(label="指导教师 (可选)")
                        cover_date = gr.Textbox(label="日期", value="2024年6月")
                        cover_university = gr.Textbox(label="学校名称 (可选)")
                        cover_type = gr.Textbox(label="论文类型", value="毕业论文（设计）")
                        cover_template = gr.Radio(["standard", "graduate"], label="封面模板", value="standard")

                        cover_btn = gr.Button("生成封面", variant="primary")

                    with gr.Column():
                        cover_output = gr.File(label="封面下载")
                        cover_status = gr.Textbox(label="状态")

                cover_btn.click(
                    fn=generate_cover,
                    inputs=[cover_title, cover_title_en, cover_author, cover_college, cover_major,
                            cover_id, cover_advisor, cover_date, cover_university, cover_type, cover_template],
                    outputs=[cover_output, cover_status],
                )

            # Tab 3: AI文档生成（对话式）
            with gr.Tab("AI文档生成"):
                gr.Markdown("### AI文档生成 - 对话式")
                gr.Markdown("输入文档描述，AI自动生成格式化的Word文档。支持多轮对话修改。")

                with gr.Row():
                    with gr.Column(scale=2):
                        # 聊天区域
                        chatbot = gr.Chatbot(
                            label="对话历史",
                            height=500,
                            type="messages",
                            show_copy_button=True,
                        )

                        with gr.Row():
                            chat_input = gr.Textbox(
                                label="输入消息",
                                placeholder="例如：写一个关于智慧城市建设的项目可行性报告...",
                                lines=2,
                                scale=4,
                            )
                            send_btn = gr.Button("发送", variant="primary", scale=1)

                        with gr.Row():
                            reset_btn = gr.Button("重新开始", size="sm")
                            export_btn = gr.Button("导出docx", variant="primary", size="sm")

                    with gr.Column(scale=1):
                        status_output = gr.Textbox(label="状态", lines=2)

                        # LLM配置
                        with gr.Accordion("LLM配置", open=True):
                            gen_provider = gr.Dropdown(
                                choices=["openai", "anthropic", "ollama"],
                                value="openai",
                                label="LLM提供商",
                            )
                            gen_key = gr.Textbox(label="API Key", type="password", placeholder="留空使用环境变量")
                            gen_model = gr.Textbox(label="模型名称", placeholder="留空使用默认模型")
                            gen_doc_type = gr.Textbox(label="文档类型", value="通用文档", placeholder="报告/公文/论文/合同等")

                        # 文档模板选择
                        doc_template_options = ["无"]
                        for t in list_doc_templates():
                            doc_template_options.append(f"{t['name']} - {t['description']}")
                        # gen_template = gr.Dropdown(
                        #     choices=doc_template_options,
                        #     value="无",
                        #     label="文档模板 (可选)",
                        # )

                        # 导出文件
                        export_file = gr.File(label="导出结果")

                # 绑定事件
                send_btn.click(
                    fn=ai_chat_send,
                    inputs=[chat_input, chatbot, session_state, gen_provider, gen_key, gen_model, gen_doc_type],
                    outputs=[chatbot, chat_input, status_output],
                )

                chat_input.submit(
                    fn=ai_chat_send,
                    inputs=[chat_input, chatbot, session_state, gen_provider, gen_key, gen_model, gen_doc_type],
                    outputs=[chatbot, chat_input, status_output],
                )

                export_btn.click(
                    fn=ai_export_docx,
                    inputs=[session_state],
                    outputs=[export_file, status_output],
                )

                reset_btn.click(
                    fn=ai_reset_session,
                    inputs=[session_state],
                    outputs=[chatbot, chat_input, status_output],
                )

            # Tab 4: 规则检查
            with gr.Tab("规则检查"):
                gr.Markdown("上传论文和自定义规则文件 (YAML)，检查是否符合要求")
                with gr.Row():
                    with gr.Column():
                        rule_paper = gr.File(label="上传论文", file_types=[".docx", ".doc", ".odt", ".rtf", ".pdf", ".txt", ".md", ".markdown"])
                        rule_file = gr.File(label="上传规则文件 (.yaml)", file_types=[".yaml", ".yml"])
                        rule_btn = gr.Button("开始检查", variant="primary")
                    with gr.Column():
                        rule_output = gr.Textbox(label="检查报告", lines=20, max_lines=30)

                rule_btn.click(
                    fn=check_rules,
                    inputs=[rule_paper, rule_file],
                    outputs=[rule_output],
                )

            # Tab 5: 使用说明
            with gr.Tab("使用说明"):
                gr.Markdown("""
## 功能说明

### 论文矫正
1. 上传待矫正的论文文件（支持 .docx / .doc / .odt / .rtf / .pdf / .txt / .md 格式）
2. 非 .docx 格式会自动转换为 .docx 后处理（.doc/.odt/.rtf 需要 LibreOffice）
3. 可选上传格式要求文档（支持 .txt / .md / .docx），工具会自动解析要求并应用
4. 可选上传自定义 config.yaml 配置文件
5. 选择是否输出质量评分和对比报告
6. 选择需要额外导出的格式（PDF/HTML/TXT/MD）
7. 点击"开始矫正"

### 封面生成
填写论文题目、作者、学院等信息，自动生成标准封面页。

### AI文档生成（对话式）
1. 输入文档描述（如"写一个项目可行性报告"）
2. AI自动识别文档类型并生成大纲
3. 确认大纲后，AI逐节生成内容
4. 支持多轮对话修改
5. 满意后点击"导出docx"下载

支持的文档类型：报告、公文、合同、方案、论文、会议纪要等。

### 规则检查
上传 YAML 格式的自定义规则文件，检查论文是否符合要求。

规则文件示例：
```yaml
rules:
  - name: "参考文献不超过50篇"
    check: reference_count
    params:
      max: 50
    severity: warning

  - name: "正文字号为小四"
    check: body_font_size
    params:
      expected: 12
    severity: error
```

### 命令行用法
```bash
python -m paper_format_corrector -f paper.docx --score --diff
python -m paper_format_corrector -r requirement.txt -f paper.docx
python -m paper_format_corrector --cover title="论文题目" author="张三"
python -m paper_format_corrector --generate "写一个项目可行性报告"  # AI生成文档
python -m paper_format_corrector --gui          # 启动 Web GUI
python -m paper_format_corrector --desktop-gui   # 启动桌面 GUI
```

---

## 联系我们

本项目为开源项目，如果您在使用过程中遇到任何问题或有任何建议，欢迎通过以下方式联系我们：

- **GitHub**: https://github.com/blankLeaving99/paper-format-corrector
- **问题反馈**: 请提交 Issue 到上述仓库，我们会第一时间处理

感谢您的使用与支持！
""")

    return app


def main():
    app = build_ui()
    port = find_free_port()
    app.launch(
        server_name="127.0.0.1",
        server_port=port,
        share=False,
        inbrowser=True,
        max_file_size="50mb",
    )


if __name__ == "__main__":
    main()
