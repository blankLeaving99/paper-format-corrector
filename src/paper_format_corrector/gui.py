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

from .app import PaperFormatCorrector
from .core.doc_generator import DocGenerator
from .core.file_converter import FileConverter
from .core.format_corrector import FormatCorrector
from .core.format_exporter import FormatExporter
from .generators.cover_page_generator import CoverPageGenerator
from .infra.doc_template_loader import list_doc_templates
from .infra.preset_loader import list_presets
from .quality.diff_reporter import DiffReporter
from .quality.quality_scorer import QualityScorer

# 全局实例
corrector = None
config_path = "config/config.yaml"

# 临时目录跟踪（退出时清理）
_temp_dirs: list[str] = []

# AI文档生成器实例（按会话管理）
_ai_sessions: dict[str, dict] = {}


def _cleanup_temp_dirs():
    for d in _temp_dirs:
        shutil.rmtree(d, ignore_errors=True)
    _temp_dirs.clear()


atexit.register(_cleanup_temp_dirs)

# 预设名称 -> ID 映射（避免字符串解析出错）
_PRESET_MAP = {}
for _p in list_presets():
    _PRESET_MAP[f"{_p['name']} - {_p['description']}"] = _p['name']



def init_corrector(config_file=None):
    global corrector, config_path
    if config_file:
        config_path = config_file
    corrector = PaperFormatCorrector(config_path)
    return corrector


def process_paper(paper_file, requirement_file, config_file, template_file, preset_name, export_formats, do_score, do_diff):
    """处理论文主函数"""
    if paper_file is None:
        return None, None, "请上传论文文件", None

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
    from .infra.path_security import validate_input_path
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
    from .parsers.ai_doc_generator import AIDocGenerator

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


def ai_chat_send_stream(
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

            # Tab 2: 封面生成
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
