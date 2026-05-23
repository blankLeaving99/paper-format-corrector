"""论文格式矫正工具 - Web GUI

基于 Gradio 的可视化界面，提供：
- 上传论文文件
- 上传需求文档（可选）
- 一键矫正
- 实时质量评分
- 对比报告预览
- 下载矫正结果

启动方式：
    python gui.py
    或
    paper-fmt-gui
"""

import tempfile
import shutil
from pathlib import Path

try:
    import gradio as gr
except ImportError:
    print("请先安装 Gradio: pip install gradio")
    print("然后运行: python gui.py")
    exit(1)

from main import PaperFormatCorrector
from quality_scorer import QualityScorer
from diff_reporter import DiffReporter
from format_exporter import FormatExporter
from cover_page_generator import CoverPageGenerator


# 全局实例
corrector = None
config_path = "config.yaml"


def init_corrector(config_file=None):
    global corrector, config_path
    if config_file:
        config_path = config_file
    corrector = PaperFormatCorrector(config_path)
    return corrector


def process_paper(paper_file, requirement_file, config_file, export_formats, do_score, do_diff):
    """处理论文主函数"""
    if paper_file is None:
        return None, None, "请上传论文文件", None

    # 初始化
    cfg = config_file.name if config_file else config_path
    c = PaperFormatCorrector(cfg)

    # 应用需求文档
    if requirement_file:
        try:
            c.apply_requirement(requirement_file.name)
        except Exception as e:
            return None, None, f"需求文档解析失败: {e}", None

    # 输出路径
    output_dir = Path(tempfile.mkdtemp())
    input_path = Path(paper_file.name)
    output_path = output_dir / f"formatted_{input_path.name}"

    # 处理
    try:
        report = c.corrector.correct_document(str(input_path), str(output_path))
    except Exception as e:
        return None, None, f"处理失败: {e}", None

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
            except Exception as e:
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

    c = PaperFormatCorrector(config_path)
    results = c.check_rules(paper_file.name, rules_path=rules_file.name)
    return c.rule_engine.format_report(results)


def build_ui():
    """构建界面"""
    with gr.Blocks(title="论文格式矫正工具", theme=gr.themes.Soft()) as app:
        gr.Markdown("# 论文格式自动矫正工具 v3.0")
        gr.Markdown("上传论文和格式要求，一键矫正论文格式")

        with gr.Tabs():
            # Tab 1: 论文矫正
            with gr.Tab("论文矫正"):
                with gr.Row():
                    with gr.Column(scale=1):
                        paper_input = gr.File(label="上传论文 (.docx)", file_types=[".docx"])
                        requirement_input = gr.File(label="格式要求文档 (可选, .txt/.md/.docx)", file_types=[".txt", ".md", ".docx"])
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
                    inputs=[paper_input, requirement_input, config_input, export_checkboxes, do_score, do_diff],
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

            # Tab 3: 规则检查
            with gr.Tab("规则检查"):
                gr.Markdown("上传论文和自定义规则文件 (YAML)，检查是否符合要求")
                with gr.Row():
                    with gr.Column():
                        rule_paper = gr.File(label="上传论文", file_types=[".docx"])
                        rule_file = gr.File(label="上传规则文件 (.yaml)", file_types=[".yaml", ".yml"])
                        rule_btn = gr.Button("开始检查", variant="primary")
                    with gr.Column():
                        rule_output = gr.Textbox(label="检查报告", lines=20, max_lines=30)

                rule_btn.click(
                    fn=check_rules,
                    inputs=[rule_paper, rule_file],
                    outputs=[rule_output],
                )

            # Tab 4: 使用说明
            with gr.Tab("使用说明"):
                gr.Markdown("""
## 功能说明

### 论文矫正
1. 上传待矫正的 .docx 论文文件
2. 可选上传格式要求文档（支持 .txt / .md / .docx），工具会自动解析要求并应用
3. 可选上传自定义 config.yaml 配置文件
4. 选择是否输出质量评分和对比报告
5. 选择需要额外导出的格式（PDF/HTML/TXT/MD）
6. 点击"开始矫正"

### 封面生成
填写论文题目、作者、学院等信息，自动生成标准封面页。

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
python main.py -f paper.docx --score --diff
python main.py -r requirement.txt -f paper.docx
python main.py --cover title="论文题目" author="张三"
```
""")

    return app


def main():
    app = build_ui()
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        inbrowser=True,
    )


if __name__ == "__main__":
    main()
