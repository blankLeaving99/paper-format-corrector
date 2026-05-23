"""论文格式矫正工具 - 桌面 GUI

基于 tkinter 的桌面可视化界面，功能与 Web GUI 一致：
- 上传论文文件（支持拖拽）
- 上传需求文档（可选，支持拖拽）
- 一键矫正
- 实时质量评分
- 对比报告预览
- 下载矫正结果

启动方式：
    python -m paper_format_corrector --desktop-gui
"""

import logging
import tempfile
import shutil
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path

# 尝试导入拖拽支持
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    HAS_DND = True
except ImportError:
    HAS_DND = False

from .app import PaperFormatCorrector
from .core.format_corrector import FormatCorrector
from .quality.quality_scorer import QualityScorer
from .quality.diff_reporter import DiffReporter
from .core.format_exporter import FormatExporter
from .generators.cover_page_generator import CoverPageGenerator
from .core.file_converter import FileConverter

# 联系我们信息
CONTACT_INFO = """联系我们

本项目为开源项目，如果您在使用过程中遇到任何问题或有任何建议，
欢迎通过以下方式联系我们：

GitHub: https://github.com/blankLeaving99/paper-format-corrector
问题反馈: 请提交 Issue 到上述仓库，我们会第一时间处理

感谢您的使用与支持！"""

CONFIG_PATH = "config/config.yaml"


class DropFileEntry(ttk.Frame):
    """支持拖拽的文件输入框组件"""

    def __init__(self, parent, label, var, filetypes=None, on_change=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.var = var
        self.filetypes = filetypes
        self.on_change = on_change

        ttk.Label(self, text=label, width=12).pack(side=tk.LEFT)
        self.entry = ttk.Entry(self, textvariable=var, width=50)
        self.entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(self, text="浏览", width=6, command=self._browse).pack(side=tk.LEFT)

        # 拖拽提示
        self.drop_label = ttk.Label(self, text="", foreground="gray", font=("Microsoft YaHei", 8))
        self.drop_label.pack(side=tk.LEFT, padx=(2, 0))

        # 绑定拖拽事件
        self._setup_dnd()

    def _setup_dnd(self):
        """设置拖拽支持"""
        if HAS_DND:
            try:
                self.entry.drop_target_register(DND_FILES)
                self.entry.dnd_bind('<<Drop>>', self._on_drop)
                self.drop_label.config(text="(可拖拽)")
            except Exception:
                self.drop_label.config(text="")
        else:
            self.drop_label.config(text="")

    def _on_drop(self, event):
        """处理拖拽放入的文件"""
        files = self._parse_dnd_data(event.data)
        if files:
            self.var.set(files[0])
            if self.on_change:
                self.on_change(files)

    @staticmethod
    def _parse_dnd_data(data):
        """解析拖拽数据，支持多个文件"""
        files = []
        if not data:
            return files

        _allowed_ext = {".docx", ".doc", ".odt", ".rtf", ".pdf", ".txt", ".md", ".markdown"}

        # Windows 拖拽格式：用 {} 包裹含空格的路径，空格分隔多个文件
        import re
        parts = re.findall(r'\{([^}]+)\}|(\S+)', data)
        for match in parts:
            path = match[0] or match[1]
            if not path:
                continue
            p = Path(path).resolve()
            # 拒绝 UNC 网络路径
            if str(p).startswith('\\\\'):
                continue
            if p.is_file() and p.suffix.lower() in _allowed_ext:
                files.append(str(p))

        return files

    def _browse(self):
        """打开文件选择对话框"""
        path = filedialog.askopenfilename(filetypes=self.filetypes)
        if path:
            self.var.set(path)
            if self.on_change:
                self.on_change([path])


class MultiDropFileEntry(ttk.Frame):
    """支持拖拽多个文件的输入框组件"""

    def __init__(self, parent, label, filetypes=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.filetypes = filetypes
        self.files = []

        # 顶部：标签 + 按钮
        top = ttk.Frame(self)
        top.pack(fill=tk.X)
        ttk.Label(top, text=label, width=12).pack(side=tk.LEFT)
        ttk.Button(top, text="添加文件", command=self._browse).pack(side=tk.LEFT, padx=5)
        ttk.Button(top, text="清空", command=self._clear).pack(side=tk.LEFT)

        if HAS_DND:
            ttk.Label(top, text="(可拖拽多个文件到下方)", foreground="gray",
                      font=("Microsoft YaHei", 8)).pack(side=tk.LEFT, padx=5)

        # 文件列表显示
        self.listbox = tk.Listbox(self, height=4, selectmode=tk.EXTENDED)
        self.listbox.pack(fill=tk.X, pady=(5, 0))

        # 拖拽支持
        if HAS_DND:
            try:
                self.listbox.drop_target_register(DND_FILES)
                self.listbox.dnd_bind('<<Drop>>', self._on_drop)
            except Exception:
                pass

    def _on_drop(self, event):
        """处理拖拽放入的文件"""
        import re
        parts = re.findall(r'\{([^}]+)\}|(\S+)', event.data)
        for match in parts:
            path = match[0] or match[1]
            if path and Path(path).exists():
                if path not in self.files:
                    self.files.append(path)
                    self.listbox.insert(tk.END, path)

    def _browse(self):
        """打开文件选择对话框"""
        paths = filedialog.askopenfilenames(filetypes=self.filetypes)
        for path in paths:
            if path not in self.files:
                self.files.append(path)
                self.listbox.insert(tk.END, path)

    def _clear(self):
        """清空文件列表"""
        self.files.clear()
        self.listbox.delete(0, tk.END)

    def get_files(self):
        """获取所有文件路径"""
        return self.files[:]


class PaperFormatDesktopApp:
    """论文格式矫正工具 - 桌面应用"""

    def __init__(self):
        if HAS_DND:
            self.root = TkinterDnD.Tk()
        else:
            self.root = tk.Tk()

        self.root.title("论文格式自动矫正工具 v3.0")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)

        # 变量
        self.paper_path = tk.StringVar()
        self.requirement_path = tk.StringVar()
        self.template_path_var = tk.StringVar()
        self.config_path = tk.StringVar(value=CONFIG_PATH)
        self.do_score = tk.BooleanVar(value=True)
        self.do_diff = tk.BooleanVar(value=True)
        self.export_pdf = tk.BooleanVar()
        self.export_html = tk.BooleanVar()
        self.export_txt = tk.BooleanVar()
        self.export_md = tk.BooleanVar()

        # 封面变量
        self.cover_title = tk.StringVar()
        self.cover_title_en = tk.StringVar()
        self.cover_author = tk.StringVar()
        self.cover_college = tk.StringVar()
        self.cover_major = tk.StringVar()
        self.cover_id = tk.StringVar()
        self.cover_advisor = tk.StringVar()
        self.cover_date = tk.StringVar(value="2024年6月")
        self.cover_university = tk.StringVar()
        self.cover_type = tk.StringVar(value="毕业论文（设计）")
        self.cover_template = tk.StringVar(value="standard")

        # 规则检查变量
        self.rule_paper_path = tk.StringVar()
        self.rule_file_path = tk.StringVar()

        self._build_ui()

    def _build_ui(self):
        """构建界面"""
        # 顶部标题
        title_frame = ttk.Frame(self.root)
        title_frame.pack(fill=tk.X, padx=10, pady=(10, 0))
        ttk.Label(title_frame, text="论文格式自动矫正工具 v3.0",
                  font=("Microsoft YaHei", 16, "bold")).pack()

        if not HAS_DND:
            hint_frame = ttk.Frame(self.root)
            hint_frame.pack(fill=tk.X, padx=10)
            ttk.Label(hint_frame, text="提示：安装 tkinterdnd2 可启用拖拽功能 (pip install tkinterdnd2)",
                      foreground="gray", font=("Microsoft YaHei", 8)).pack()

        # 标签页
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self._build_correct_tab(notebook)
        self._build_cover_tab(notebook)
        self._build_rule_tab(notebook)
        self._build_help_tab(notebook)

    # ── Tab 1: 论文矫正 ──────────────────────────────────────

    def _build_correct_tab(self, notebook):
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="论文矫正")

        # 文件选择区
        file_frame = ttk.LabelFrame(tab, text="文件选择", padding=10)
        file_frame.pack(fill=tk.X, padx=10, pady=5)

        # 论文文件 - 支持拖拽
        self.paper_entry = DropFileEntry(
            file_frame, "论文文件:", self.paper_path,
            filetypes=[("所有支持格式", "*.docx *.doc *.odt *.rtf *.pdf *.txt *.md"),
                       ("Word文档", "*.docx *.doc"), ("PDF文件", "*.pdf"),
                       ("文本文件", "*.txt *.md"), ("所有文件", "*.*")]
        )
        self.paper_entry.pack(fill=tk.X, pady=3)

        # 模板文件 - 支持拖拽
        self.template_entry = DropFileEntry(
            file_frame, "模板文件:", self.template_path_var,
            filetypes=[("Word文档", "*.docx"), ("所有文件", "*.*")]
        )
        self.template_entry.pack(fill=tk.X, pady=3)

        # 格式要求 - 支持拖拽
        self.req_entry = DropFileEntry(
            file_frame, "格式要求:", self.requirement_path,
            filetypes=[("文档文件", "*.txt *.md *.docx *.pdf"), ("所有文件", "*.*")]
        )
        self.req_entry.pack(fill=tk.X, pady=3)

        # 自定义配置
        self.cfg_entry = DropFileEntry(
            file_frame, "自定义配置:", self.config_path,
            filetypes=[("YAML文件", "*.yaml *.yml"), ("所有文件", "*.*")]
        )
        self.cfg_entry.pack(fill=tk.X, pady=3)

        # 选项区
        opt_frame = ttk.LabelFrame(tab, text="处理选项", padding=10)
        opt_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Checkbutton(opt_frame, text="输出质量评分", variable=self.do_score).pack(side=tk.LEFT, padx=10)
        ttk.Checkbutton(opt_frame, text="生成对比报告", variable=self.do_diff).pack(side=tk.LEFT, padx=10)

        export_frame = ttk.Frame(opt_frame)
        export_frame.pack(side=tk.LEFT, padx=20)
        ttk.Label(export_frame, text="导出格式:").pack(side=tk.LEFT)
        ttk.Checkbutton(export_frame, text="PDF", variable=self.export_pdf).pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(export_frame, text="HTML", variable=self.export_html).pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(export_frame, text="TXT", variable=self.export_txt).pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(export_frame, text="MD", variable=self.export_md).pack(side=tk.LEFT, padx=5)

        # 操作按钮
        btn_frame = ttk.Frame(tab)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Button(btn_frame, text="开始矫正", command=self._run_correct).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="批量矫正（选择多个文件）", command=self._run_batch_correct).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="打开结果目录", command=lambda: self._open_dir("output")).pack(side=tk.LEFT, padx=5)

        # 结果区
        result_frame = ttk.LabelFrame(tab, text="处理结果", padding=10)
        result_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.result_text = scrolledtext.ScrolledText(result_frame, height=15, font=("Consolas", 10))
        self.result_text.pack(fill=tk.BOTH, expand=True)

    # ── Tab 2: 封面生成 ──────────────────────────────────────

    def _build_cover_tab(self, notebook):
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="封面生成")

        # 表单
        form_frame = ttk.LabelFrame(tab, text="论文信息", padding=10)
        form_frame.pack(fill=tk.X, padx=10, pady=5)

        fields = [
            ("论文题目:", self.cover_title),
            ("英文题目:", self.cover_title_en),
            ("作者姓名:", self.cover_author),
            ("学院:", self.cover_college),
            ("专业:", self.cover_major),
            ("学号:", self.cover_id),
            ("指导教师:", self.cover_advisor),
            ("日期:", self.cover_date),
            ("学校名称:", self.cover_university),
            ("论文类型:", self.cover_type),
        ]

        for i, (label, var) in enumerate(fields):
            row = ttk.Frame(form_frame)
            row.pack(fill=tk.X, pady=2)
            ttk.Label(row, text=label, width=12).pack(side=tk.LEFT)
            ttk.Entry(row, textvariable=var, width=50).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        # 模板选择
        tpl_frame = ttk.Frame(form_frame)
        tpl_frame.pack(fill=tk.X, pady=5)
        ttk.Label(tpl_frame, text="封面模板:", width=12).pack(side=tk.LEFT)
        ttk.Radiobutton(tpl_frame, text="标准", variable=self.cover_template, value="standard").pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(tpl_frame, text="研究生", variable=self.cover_template, value="graduate").pack(side=tk.LEFT, padx=10)

        # 按钮
        btn_frame = ttk.Frame(tab)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Button(btn_frame, text="生成封面", command=self._run_cover).pack(side=tk.LEFT, padx=5)

        # 结果
        self.cover_status = ttk.Label(tab, text="", font=("Microsoft YaHei", 10))
        self.cover_status.pack(padx=10, pady=5)

    # ── Tab 3: 规则检查 ──────────────────────────────────────

    def _build_rule_tab(self, notebook):
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="规则检查")

        # 文件选择
        file_frame = ttk.LabelFrame(tab, text="文件选择", padding=10)
        file_frame.pack(fill=tk.X, padx=10, pady=5)

        self.rule_paper_entry = DropFileEntry(
            file_frame, "论文文件:", self.rule_paper_path,
            filetypes=[("所有支持格式", "*.docx *.doc *.odt *.rtf *.pdf *.txt *.md"),
                       ("所有文件", "*.*")]
        )
        self.rule_paper_entry.pack(fill=tk.X, pady=3)

        self.rule_file_entry = DropFileEntry(
            file_frame, "规则文件:", self.rule_file_path,
            filetypes=[("YAML文件", "*.yaml *.yml"), ("所有文件", "*.*")]
        )
        self.rule_file_entry.pack(fill=tk.X, pady=3)

        # 按钮
        btn_frame = ttk.Frame(tab)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Button(btn_frame, text="开始检查", command=self._run_rule_check).pack(side=tk.LEFT, padx=5)

        # 结果
        result_frame = ttk.LabelFrame(tab, text="检查报告", padding=10)
        result_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.rule_result_text = scrolledtext.ScrolledText(result_frame, height=15, font=("Consolas", 10))
        self.rule_result_text.pack(fill=tk.BOTH, expand=True)

    # ── Tab 4: 使用说明 ──────────────────────────────────────

    def _build_help_tab(self, notebook):
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="使用说明")

        text = scrolledtext.ScrolledText(tab, font=("Microsoft YaHei", 10), wrap=tk.WORD)
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        dnd_hint = "（已启用拖拽功能，可直接拖拽文件到输入框）" if HAS_DND else "（安装 tkinterdnd2 可启用拖拽：pip install tkinterdnd2）"

        help_content = f"""论文格式自动矫正工具 v3.0 - 使用说明

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

拖拽功能：{dnd_hint}

【论文矫正】
1. 拖拽或选择论文文件（支持 .docx/.doc/.odt/.rtf/.pdf/.txt/.md）
2. 可选拖拽格式要求文档（支持 .txt/.md/.docx/.pdf）
3. 可选拖拽自定义 config.yaml 配置文件
4. 选择处理选项，点击"开始矫正"或"批量矫正"

【批量处理】
- 点击"批量矫正"按钮，可选择多个文件一次性处理
- 也可将多个文件拖拽到论文文件输入框（会自动识别）

【封面生成】
填写论文信息，点击"生成封面"自动生成标准封面页。

【规则检查】
拖拽论文文件和 YAML 规则文件，点击"开始检查"。

【命令行用法】
  python run.py                              # 启动选择器
  python main.py -f paper.docx --score       # 命令行模式
  python gui.py                              # 直接启动 Web GUI

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{CONTACT_INFO}"""

        text.insert(tk.END, help_content)
        text.config(state=tk.DISABLED)

    # ── 核心功能 ──────────────────────────────────────────────

    def _run_correct(self):
        """执行单个论文矫正"""
        paper = self.paper_path.get().strip()
        if not paper:
            messagebox.showwarning("提示", "请先选择或拖拽论文文件")
            return

        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, "正在处理，请稍候...\n")
        self.root.update()

        def do_work():
            try:
                result = self._process_single(paper)
                self.root.after(0, lambda: self._show_result(result))
            except Exception as e:
                logging.getLogger(__name__).exception("处理失败")
                self.root.after(0, lambda: self._show_result("处理失败，请检查输入文件是否正确。"))

        threading.Thread(target=do_work, daemon=True).start()

    def _run_batch_correct(self):
        """批量矫正 - 选择多个文件"""
        filetypes = [
            ("所有支持格式", "*.docx *.doc *.odt *.rtf *.pdf *.txt *.md"),
            ("Word文档", "*.docx *.doc"), ("PDF文件", "*.pdf"),
            ("文本文件", "*.txt *.md"), ("所有文件", "*.*")
        ]
        files = filedialog.askopenfilenames(filetypes=filetypes, title="选择多个论文文件")
        if not files:
            return

        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, f"已选择 {len(files)} 个文件，开始批量处理...\n\n")
        self.root.update()

        def do_work():
            results = []
            for i, paper in enumerate(files, 1):
                self.root.after(0, lambda p=paper, idx=i: self._show_result(
                    f"[{idx}/{len(files)}] 正在处理: {Path(p).name}...\n"))
                try:
                    result = self._process_single(paper)
                    results.append(f"[{i}/{len(files)}] {Path(p).name}\n{result}\n")
                except Exception as e:
                    results.append(f"[{i}/{len(files)}] {Path(p).name} - 失败: {e}\n")

            final = "\n" + "=" * 60 + "\n批量处理完成\n" + "=" * 60 + "\n\n" + "\n".join(results)
            self.root.after(0, lambda: self._show_result(final))

        threading.Thread(target=do_work, daemon=True).start()

    def _process_single(self, paper):
        """处理单个文件，返回结果文本"""
        cfg = self.config_path.get().strip() or CONFIG_PATH
        c = PaperFormatCorrector(cfg)

        # 覆盖模板文件
        tpl = self.template_path_var.get().strip()
        if tpl:
            c.template_path = tpl
            c.corrector = FormatCorrector(tpl, c.config)

        # 应用需求文档
        req = self.requirement_path.get().strip()
        if req:
            c.apply_requirement(req)

        # 格式转换
        input_path = Path(paper)
        converter = FileConverter()
        if converter.needs_conversion(str(input_path)):
            tmp_dir = Path(tempfile.mkdtemp())
            converted = converter.convert(str(input_path), str(tmp_dir))
            input_path = Path(converted)

        # 输出路径
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / f"formatted_{input_path.name}"

        # 处理
        report = c.corrector.correct_document(str(input_path), str(output_path))

        # 质量评分
        score_report = ""
        if self.do_score.get():
            scorer = QualityScorer(c.config)
            total, scores, issues = scorer.score(str(output_path))
            score_report = scorer.format_report(total, scores, issues)

        # 对比报告
        diff_path = None
        if self.do_diff.get():
            diff_path = str(output_path.with_suffix(".diff.html"))
            reporter = DiffReporter()
            orig_path = str(output_path) + ".orig.docx"
            shutil.copy2(str(input_path), orig_path)
            reporter.generate_html_report(orig_path, str(output_path), diff_path)
            Path(orig_path).unlink(missing_ok=True)

        # 导出
        export_formats = []
        if self.export_pdf.get(): export_formats.append("pdf")
        if self.export_html.get(): export_formats.append("html")
        if self.export_txt.get(): export_formats.append("txt")
        if self.export_md.get(): export_formats.append("md")

        if export_formats:
            exporter = FormatExporter()
            for fmt in export_formats:
                out = output_path.with_suffix(f".{fmt}")
                try:
                    exporter.export(str(output_path), str(out), fmt)
                except Exception:
                    pass

        # 构建结果
        lines = [
            f"{'=' * 50}",
            f"处理完成: {input_path.name}",
            f"{'=' * 50}",
            f"输出文件: {output_path}",
            "",
            f"矫正段落数: {report['paragraphs_corrected']}",
            f"标题矫正:   {report['headings_fixed']}",
            f"正文矫正:   {report['body_fixed']}",
        ]
        if report.get("tables_formatted"):
            lines.append(f"表格格式化: {report['tables_formatted']}")
        if report.get("images_centered"):
            lines.append(f"图片居中:   {report['images_centered']}")
        if report.get("fig_table_issues"):
            lines.append(f"\n图表编号修正 ({len(report['fig_table_issues'])} 项):")
            for issue in report["fig_table_issues"]:
                lines.append(f"  - {issue}")
        if report.get("ref_issues"):
            lines.append(f"\n参考文献问题 ({len(report['ref_issues'])} 项):")
            for issue in report["ref_issues"]:
                lines.append(f"  - {issue}")
        if diff_path:
            lines.append(f"\n对比报告: {diff_path}")
        if score_report:
            lines.append(f"\n{score_report}")

        return "\n".join(lines)

    def _run_cover(self):
        """生成封面"""
        title = self.cover_title.get().strip()
        if not title:
            messagebox.showwarning("提示", "请填写论文题目")
            return

        metadata = {
            "title": title,
            "title_en": self.cover_title_en.get().strip(),
            "author": self.cover_author.get().strip(),
            "college": self.cover_college.get().strip(),
            "major": self.cover_major.get().strip(),
            "student_id": self.cover_id.get().strip(),
            "advisor": self.cover_advisor.get().strip(),
            "date": self.cover_date.get().strip(),
            "university": self.cover_university.get().strip(),
            "paper_type": self.cover_type.get().strip(),
        }

        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / "cover.docx"

        try:
            generator = CoverPageGenerator()
            generator.generate(metadata, str(output_path), self.cover_template.get())
            self.cover_status.config(text=f"封面已生成: {output_path}")
            messagebox.showinfo("成功", f"封面已生成:\n{output_path.resolve()}")
        except Exception as e:
            logging.getLogger(__name__).exception("封面生成失败")
            self.cover_status.config(text="生成失败，请检查输入信息。")
            messagebox.showerror("错误", "封面生成失败，请检查输入信息。")

    def _run_rule_check(self):
        """执行规则检查"""
        paper = self.rule_paper_path.get().strip()
        rules = self.rule_file_path.get().strip()

        if not paper:
            messagebox.showwarning("提示", "请先选择或拖拽论文文件")
            return
        if not rules:
            messagebox.showwarning("提示", "请先选择或拖拽规则文件")
            return

        self.rule_result_text.delete(1.0, tk.END)
        self.rule_result_text.insert(tk.END, "正在检查，请稍候...\n")
        self.root.update()

        def do_work():
            try:
                input_path = paper
                converter = FileConverter()
                if converter.needs_conversion(input_path):
                    tmp_dir = Path(tempfile.mkdtemp())
                    input_path = converter.convert(input_path, str(tmp_dir))

                c = PaperFormatCorrector(CONFIG_PATH)
                results = c.check_rules(input_path, rules_path=rules)
                report = c.rule_engine.format_report(results)
                self.root.after(0, lambda: self._show_rule_result(report))
            except Exception as e:
                self.root.after(0, lambda: self._show_rule_result(f"检查失败: {e}"))

        threading.Thread(target=do_work, daemon=True).start()

    def _show_result(self, text):
        """显示处理结果"""
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, text)

    def _show_rule_result(self, text):
        """显示规则检查结果"""
        self.rule_result_text.delete(1.0, tk.END)
        self.rule_result_text.insert(tk.END, text)

    def _open_dir(self, dir_path):
        """打开目录"""
        import os
        path = Path(dir_path).resolve()
        if path.exists():
            os.startfile(str(path))
        else:
            messagebox.showinfo("提示", f"目录不存在: {path}")

    def run(self):
        """启动应用"""
        self.root.mainloop()


def main():
    app = PaperFormatDesktopApp()
    app.run()


if __name__ == "__main__":
    main()
