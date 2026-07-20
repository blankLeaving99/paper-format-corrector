"""论文格式矫正工具 - 桌面 GUI v2

基于 tkinter 的桌面可视化界面，功能与 Web GUI 一致：
- 上传论文文件（支持拖拽）
- 上传需求文档（可选，支持拖拽）
- 一键矫正
- 实时质量评分
- 对比报告预览
- 下载矫正结果
- AI文档生成（对话式，流式输出）

启动方式：
    python -m paper_format_corrector --desktop-gui
"""

import logging
import shutil
import tempfile
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

# 尝试导入拖拽支持
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except ImportError:
    HAS_DND = False

from .app import PaperFormatCorrector
from .application.services.style_workbench import (
    build_application_report,
    build_correction_plan,
    explain_style_profile,
    learn_style_profile,
    manual_style_config,
    scan_document,
)
from .core.doc_generator import DocGenerator
from .core.file_converter import FileConverter
from .core.format_corrector import FormatCorrector
from .core.format_exporter import FormatExporter
from .generators.cover_page_generator import CoverPageGenerator
from .infra.doc_template_loader import list_doc_templates
from .infra.template_repository import TemplateRepository
from .quality.diff_reporter import DiffReporter
from .quality.quality_scorer import QualityScorer

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
        _allowed_ext = {".docx", ".doc", ".odt", ".rtf", ".pdf", ".txt", ".md", ".markdown"}
        parts = re.findall(r'\{([^}]+)\}|(\S+)', event.data)
        for match in parts:
            path = match[0] or match[1]
            if not path:
                continue
            p = Path(path).resolve()
            if str(p).startswith('\\\\'):
                continue
            if p.is_file() and p.suffix.lower() in _allowed_ext:
                if str(p) not in self.files:
                    self.files.append(str(p))
                    self.listbox.insert(tk.END, str(p))

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

        # 格式工作台变量
        self.wb_paper_path = tk.StringVar()
        self.wb_sample_path = tk.StringVar()
        self.wb_body_font = tk.StringVar(value="宋体")
        self.wb_heading_font = tk.StringVar(value="黑体")
        self.wb_body_size = tk.DoubleVar(value=12)
        self.wb_line_spacing = tk.DoubleVar(value=1.5)
        self.wb_indent = tk.DoubleVar(value=2)
        self.wb_heading1_size = tk.DoubleVar(value=16)
        self.wb_heading2_size = tk.DoubleVar(value=14)
        self.wb_heading3_size = tk.DoubleVar(value=12)
        self.wb_table_style = tk.StringVar(value="three_line")
        self.wb_table_size = tk.DoubleVar(value=10.5)
        self.wb_image_width = tk.StringVar(value="full")
        self.wb_template_choice = tk.StringVar(value="无（使用默认配置）")
        self.wb_template_name = tk.StringVar()

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

        # AI文档生成变量
        self.gen_doc_type = tk.StringVar(value="通用文档")
        self.gen_template = tk.StringVar(value="无")
        self.gen_provider = tk.StringVar(value="openai")
        self.gen_key = tk.StringVar()
        self.gen_model = tk.StringVar()

        # AI对话状态
        self._ai_session = None
        self._ai_outline = None
        self._ai_structure = None

        # 预览数据
        self._last_report = None
        self._last_diff_path = None
        self._last_score_report = ""

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
        self._build_workbench_tab(notebook)
        self._build_preview_tab(notebook)
        self._build_history_tab(notebook)
        self._build_cover_tab(notebook)
        self._build_ai_gen_tab(notebook)
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
        self.correct_btn = ttk.Button(btn_frame, text="开始矫正", command=self._run_correct)
        self.correct_btn.pack(side=tk.LEFT, padx=5)
        self.batch_btn = ttk.Button(btn_frame, text="批量矫正（选择多个文件）", command=self._run_batch_correct)
        self.batch_btn.pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="打开结果目录", command=lambda: self._open_dir("output")).pack(side=tk.LEFT, padx=5)

        # 结果区
        result_frame = ttk.LabelFrame(tab, text="处理结果", padding=10)
        result_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.result_text = scrolledtext.ScrolledText(result_frame, height=15, font=("Consolas", 10))
        self.result_text.pack(fill=tk.BOTH, expand=True)

    # ── Tab 2: 格式工作台 ──────────────────────────────────────

    def _build_workbench_tab(self, notebook):
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="格式工作台")

        files = ttk.LabelFrame(tab, text="文档与样本", padding=10)
        files.pack(fill=tk.X, padx=10, pady=5)
        DropFileEntry(files, "待处理论文:", self.wb_paper_path, filetypes=[("Word文档", "*.docx")]).pack(fill=tk.X, pady=2)
        DropFileEntry(files, "样本文档:", self.wb_sample_path, filetypes=[("Word文档", "*.docx")]).pack(fill=tk.X, pady=2)
        template_row = ttk.Frame(files)
        template_row.pack(fill=tk.X, pady=2)
        ttk.Label(template_row, text="模板库:", width=12).pack(side=tk.LEFT)
        self.wb_template_box = ttk.Combobox(template_row, textvariable=self.wb_template_choice, values=self._workbench_template_choices(), width=55, state="readonly")
        self.wb_template_box.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        styles = ttk.LabelFrame(tab, text="全局样式（应用到全部同类元素）", padding=10)
        styles.pack(fill=tk.X, padx=10, pady=5)
        fields = [
            ("正文字体", self.wb_body_font), ("正文字号(pt)", self.wb_body_size),
            ("正文行距", self.wb_line_spacing), ("首行缩进(字符)", self.wb_indent),
            ("标题字体", self.wb_heading_font), ("一级标题(pt)", self.wb_heading1_size),
            ("二级标题(pt)", self.wb_heading2_size), ("三级标题(pt)", self.wb_heading3_size),
            ("表格字号(pt)", self.wb_table_size),
        ]
        for index, (label, variable) in enumerate(fields):
            row, col = divmod(index, 3)
            ttk.Label(styles, text=label).grid(row=row, column=col * 2, sticky=tk.W, padx=4, pady=3)
            ttk.Entry(styles, textvariable=variable, width=12).grid(row=row, column=col * 2 + 1, sticky=tk.W, padx=4, pady=3)
        ttk.Label(styles, text="表格样式").grid(row=3, column=0, sticky=tk.W, padx=4, pady=3)
        ttk.Combobox(styles, textvariable=self.wb_table_style, values=["three_line", "full_border", "keep"], width=12, state="readonly").grid(row=3, column=1, sticky=tk.W)
        ttk.Label(styles, text="图片最大宽度").grid(row=3, column=2, sticky=tk.W, padx=4, pady=3)
        ttk.Combobox(styles, textvariable=self.wb_image_width, values=["full", "90%", "80%", "70%", "50%"], width=12, state="readonly").grid(row=3, column=3, sticky=tk.W)

        actions = ttk.Frame(tab)
        actions.pack(fill=tk.X, padx=10, pady=5)
        ttk.Button(actions, text="扫描论文", command=self._scan_workbench).pack(side=tk.LEFT, padx=5)
        ttk.Button(actions, text="预览矫正计划", command=self._preview_workbench_plan).pack(side=tk.LEFT, padx=5)
        ttk.Button(actions, text="查看样本学习结果", command=self._inspect_workbench_sample).pack(side=tk.LEFT, padx=5)
        ttk.Button(actions, text="保存样本为我的模板", command=self._save_workbench_template).pack(side=tk.LEFT, padx=5)
        ttk.Button(actions, text="应用到全部同类元素", command=self._run_workbench).pack(side=tk.LEFT, padx=5)

        ttk.Entry(actions, textvariable=self.wb_template_name, width=22).pack(side=tk.RIGHT, padx=5)
        ttk.Label(actions, text="个人模板名称:").pack(side=tk.RIGHT)

        self.workbench_text = scrolledtext.ScrolledText(tab, height=16, font=("Consolas", 10))
        self.workbench_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

    def _write_workbench(self, text):
        self.workbench_text.delete(1.0, tk.END)
        self.workbench_text.insert(tk.END, text)

    @staticmethod
    def _workbench_template_choices():
        choices = ["无（使用默认配置）"]
        for template in TemplateRepository().list_templates():
            choices.append(f"{template.slug} | [{template.category}] {template.name}")
        return choices

    def _save_workbench_template(self):
        sample = self.wb_sample_path.get().strip()
        if not sample:
            messagebox.showwarning("提示", "请先选择已排好版的样本文档")
            return
        try:
            record = TemplateRepository().save_personal_template(
                self.wb_template_name.get().strip() or Path(sample).stem,
                "高校毕业论文", learn_style_profile(sample), "由样本文档自动学习",
            )
            self.wb_template_box.configure(values=self._workbench_template_choices())
            self.wb_template_choice.set(f"{record.slug} | [{record.category}] {record.name}")
            self._write_workbench(f"已保存个人模板：{record.name}")
        except Exception as exc:
            self._write_workbench(f"保存模板失败：{exc}")

    def _scan_workbench(self):
        path = self.wb_paper_path.get().strip()
        if not path:
            messagebox.showwarning("提示", "请先选择 .docx 论文")
            return
        try:
            import json
            self._write_workbench(json.dumps(scan_document(path), ensure_ascii=False, indent=2, default=str))
        except Exception as exc:
            self._write_workbench(f"扫描失败：{exc}")

    def _preview_workbench_plan(self):
        """预览矫正计划（dry-run）"""
        path = self.wb_paper_path.get().strip()
        if not path:
            messagebox.showwarning("提示", "请先选择 .docx 论文")
            return
        self._write_workbench("正在生成矫正计划，请稍候…")

        def do_plan():
            try:
                c = PaperFormatCorrector(CONFIG_PATH)
                choice = self.wb_template_choice.get()
                if choice != "无（使用默认配置）":
                    stored = TemplateRepository().get(choice.split(" | ", 1)[0])
                    if stored is not None:
                        c.config = c._merge_config(c.config, stored.config)
                sample = self.wb_sample_path.get().strip()
                if sample:
                    c.config = c._merge_config(c.config, learn_style_profile(sample))
                c.config = c._merge_config(c.config, manual_style_config(
                    self.wb_body_font.get(), self.wb_body_size.get(), self.wb_line_spacing.get(), self.wb_indent.get(),
                    self.wb_heading1_size.get(), self.wb_heading2_size.get(), self.wb_heading3_size.get(), self.wb_heading_font.get(),
                    self.wb_table_style.get(), self.wb_table_size.get(), self.wb_image_width.get(),
                ))
                plan = build_correction_plan(path, c.config.get("format_rules", {}))
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
                self.root.after(0, lambda: self._write_workbench("\n".join(lines)))
            except Exception as exc:
                err_msg = f"生成计划失败：{exc}"
                self.root.after(0, lambda m=err_msg: self._write_workbench(m))

        threading.Thread(target=do_plan, daemon=True).start()

    def _inspect_workbench_sample(self):
        path = self.wb_sample_path.get().strip()
        if not path:
            messagebox.showwarning("提示", "请先选择已排好版的 .docx 样本文档")
            return
        try:
            import json
            self._write_workbench(json.dumps(explain_style_profile(path), ensure_ascii=False, indent=2, default=str))
        except Exception as exc:
            self._write_workbench(f"样式学习失败：{exc}")

    def _run_workbench(self):
        paper = self.wb_paper_path.get().strip()
        if not paper:
            messagebox.showwarning("提示", "请先选择 .docx 论文")
            return
        self._write_workbench("正在应用格式，请稍候…")

        def do_work():
            try:
                c = PaperFormatCorrector(CONFIG_PATH)
                choice = self.wb_template_choice.get()
                if choice != "无（使用默认配置）":
                    stored = TemplateRepository().get(choice.split(" | ", 1)[0])
                    if stored is None:
                        raise ValueError("所选模板不存在，请刷新模板库后重试")
                    c.config = c._merge_config(c.config, stored.config)
                sample = self.wb_sample_path.get().strip()
                if sample:
                    c.config = c._merge_config(c.config, learn_style_profile(sample))
                c.config = c._merge_config(c.config, manual_style_config(
                    self.wb_body_font.get(), self.wb_body_size.get(), self.wb_line_spacing.get(), self.wb_indent.get(),
                    self.wb_heading1_size.get(), self.wb_heading2_size.get(), self.wb_heading3_size.get(), self.wb_heading_font.get(),
                    self.wb_table_style.get(), self.wb_table_size.get(), self.wb_image_width.get(),
                ))
                c.corrector = FormatCorrector(c.template_path, c.config)
                output_dir = Path("output")
                output_dir.mkdir(exist_ok=True)
                output = output_dir / f"workbench_{Path(paper).name}"
                report = c.corrector.correct_document(paper, str(output))
                import json
                text = f"已生成：{output}\n\n" + json.dumps(build_application_report(paper, report), ensure_ascii=False, indent=2, default=str)
                self.root.after(0, lambda: self._write_workbench(text))
            except Exception as exc:
                error_text = f"应用格式失败：{exc}"
                self.root.after(0, lambda: self._write_workbench(error_text))

        threading.Thread(target=do_work, daemon=True).start()

    # ── Tab 3: 矫正预览 ──────────────────────────────────────

    def _build_preview_tab(self, notebook):
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="矫正预览")

        # 刷新按钮
        btn_frame = ttk.Frame(tab)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Button(btn_frame, text="刷新预览", command=self._refresh_preview).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="打开对比报告", command=self._open_diff_report).pack(side=tk.LEFT, padx=5)

        # 分栏：左侧建议列表，右侧评分报告
        paned = ttk.PanedWindow(tab, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 左侧：矫正建议列表
        left_frame = ttk.LabelFrame(paned, text="矫正建议", padding=5)
        self.preview_tree = ttk.Treeview(left_frame, columns=("type", "message"), show="headings", height=15)
        self.preview_tree.heading("type", text="类型")
        self.preview_tree.heading("message", text="描述")
        self.preview_tree.column("type", width=80, anchor="center")
        self.preview_tree.column("message", width=400)
        scrollbar = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.preview_tree.yview)
        self.preview_tree.configure(yscrollcommand=scrollbar.set)
        self.preview_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        paned.add(left_frame, weight=1)

        # 右侧：评分报告
        right_frame = ttk.LabelFrame(paned, text="质量评分", padding=5)
        self.preview_score_text = scrolledtext.ScrolledText(right_frame, height=15, font=("Consolas", 10))
        self.preview_score_text.pack(fill=tk.BOTH, expand=True)
        paned.add(right_frame, weight=1)

    def _refresh_preview(self):  # noqa: C901
        """刷新矫正预览"""
        # 清空
        for item in self.preview_tree.get_children():
            self.preview_tree.delete(item)
        self.preview_score_text.delete(1.0, tk.END)

        if self._last_report is None:
            self.preview_score_text.insert(tk.END, "请先执行论文矫正")
            return

        report = self._last_report

        # 填充建议列表
        suggestions = []
        if report.get("fig_table_issues"):
            for issue in report["fig_table_issues"]:
                suggestions.append(("图表", issue))
        if report.get("ref_issues"):
            for issue in report["ref_issues"]:
                suggestions.append(("文献", issue))
        if report.get("warnings"):
            for w in report["warnings"]:
                suggestions.append(("警告", w))

        # 统计信息
        suggestions.append(("统计", f"矫正段落: {report.get('paragraphs_corrected', 0)}"))
        suggestions.append(("统计", f"标题矫正: {report.get('headings_fixed', 0)}"))
        suggestions.append(("统计", f"正文矫正: {report.get('body_fixed', 0)}"))
        if report.get("tables_formatted"):
            suggestions.append(("统计", f"表格格式化: {report['tables_formatted']}"))
        if report.get("images_centered"):
            suggestions.append(("统计", f"图片居中: {report['images_centered']}"))
        if report.get("citation_style"):
            suggestions.append(("统计", f"引用风格: {report['citation_style']}"))

        for typ, msg in suggestions:
            self.preview_tree.insert("", tk.END, values=(typ, msg))

        # 填充评分报告
        if self._last_score_report:
            self.preview_score_text.insert(tk.END, self._last_score_report)
        else:
            self.preview_score_text.insert(tk.END, "未启用质量评分（矫正时勾选'输出质量评分'）")

    def _open_diff_report(self):
        """打开对比报告"""
        if self._last_diff_path and Path(self._last_diff_path).exists():
            import os
            os.startfile(str(self._last_diff_path))
        else:
            messagebox.showinfo("提示", "无对比报告（矫正时勾选'生成对比报告'）")

    # ── Tab 4: 报告中心 ──────────────────────────────────────

    def _build_history_tab(self, notebook):
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="报告中心")

        btn_frame = ttk.Frame(tab)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Button(btn_frame, text="刷新列表", command=self._refresh_history).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="查看详情", command=self._view_history_detail).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="删除记录", command=self._delete_history).pack(side=tk.LEFT, padx=5)

        tree_frame = ttk.Frame(tab)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.history_tree = ttk.Treeview(
            tree_frame,
            columns=("id", "input", "status", "score", "time", "created"),
            show="headings", height=18,
        )
        self.history_tree.heading("id", text="ID")
        self.history_tree.heading("input", text="输入文件")
        self.history_tree.heading("status", text="状态")
        self.history_tree.heading("score", text="质量评分")
        self.history_tree.heading("time", text="耗时(s)")
        self.history_tree.heading("created", text="处理时间")
        self.history_tree.column("id", width=50, anchor="center")
        self.history_tree.column("input", width=250)
        self.history_tree.column("status", width=70, anchor="center")
        self.history_tree.column("score", width=80, anchor="center")
        self.history_tree.column("time", width=70, anchor="center")
        self.history_tree.column("created", width=150)
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=scrollbar.set)
        self.history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.history_detail_text = scrolledtext.ScrolledText(tab, height=10, font=("Consolas", 10))
        self.history_detail_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self._refresh_history()

    def _refresh_history(self):
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        try:
            records = TemplateRepository().list_processing_history(limit=100)
            for r in records:
                self.history_tree.insert("", tk.END, values=(
                    r["id"], Path(r["input_file"]).name, r["status"],
                    f"{r['quality_score']:.1f}" if r["quality_score"] else "-",
                    f"{r['processing_time']:.1f}" if r["processing_time"] else "-",
                    r["created_at"][:19] if r["created_at"] else "",
                ))
        except Exception as exc:
            self.history_detail_text.delete(1.0, tk.END)
            self.history_detail_text.insert(tk.END, f"加载历史记录失败: {exc}")

    def _view_history_detail(self):
        sel = self.history_tree.selection()
        if not sel:
            messagebox.showinfo("提示", "请先选择一条记录")
            return
        record_id = int(self.history_tree.item(sel[0])["values"][0])
        try:
            record = TemplateRepository().get_processing_history(record_id)
            if not record:
                return
            import json
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
            self.history_detail_text.delete(1.0, tk.END)
            self.history_detail_text.insert(tk.END, "\n".join(lines))
        except Exception as exc:
            self.history_detail_text.delete(1.0, tk.END)
            self.history_detail_text.insert(tk.END, f"加载详情失败: {exc}")

    def _delete_history(self):
        sel = self.history_tree.selection()
        if not sel:
            messagebox.showinfo("提示", "请先选择一条记录")
            return
        if not messagebox.askyesno("确认", "确定删除选中的记录？"):
            return
        for item in sel:
            record_id = int(self.history_tree.item(item)["values"][0])
            TemplateRepository().delete_processing_history(record_id)
        self._refresh_history()

    # ── Tab 3: 封面生成 ──────────────────────────────────────

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

        for _i, (label, var) in enumerate(fields):
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

    # ── Tab 4: AI文档生成（对话式） ────────────────────────────

    def _build_ai_gen_tab(self, notebook):
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="AI文档生成")

        # 主面板：左侧聊天区，右侧配置区
        main_paned = ttk.PanedWindow(tab, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # ── 左侧：聊天区 ──
        left_frame = ttk.Frame(main_paned)
        main_paned.add(left_frame, weight=3)

        # 聊天历史显示
        chat_label = ttk.LabelFrame(left_frame, text="对话历史", padding=5)
        chat_label.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.chat_display = scrolledtext.ScrolledText(
            chat_label, height=20, font=("Microsoft YaHei", 10),
            wrap=tk.WORD, state=tk.DISABLED
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True)

        # 配置聊天显示区域的标签样式
        self.chat_display.tag_configure("user_name", foreground="#2196F3", font=("Microsoft YaHei", 10, "bold"))
        self.chat_display.tag_configure("ai_name", foreground="#4CAF50", font=("Microsoft YaHei", 10, "bold"))
        self.chat_display.tag_configure("system_msg", foreground="#FF9800", font=("Microsoft YaHei", 9, "italic"))

        # 输入区
        input_frame = ttk.Frame(left_frame)
        input_frame.pack(fill=tk.X, padx=5, pady=5)

        self.chat_input = tk.Text(input_frame, height=3, font=("Microsoft YaHei", 10), wrap=tk.WORD)
        self.chat_input.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        # 按钮区
        btn_frame = ttk.Frame(input_frame)
        btn_frame.pack(side=tk.RIGHT)

        self.send_btn = ttk.Button(btn_frame, text="发送", command=self._ai_chat_send)
        self.send_btn.pack(pady=2)

        self.confirm_btn = ttk.Button(btn_frame, text="确认大纲", command=self._ai_confirm_outline, state=tk.DISABLED)
        self.confirm_btn.pack(pady=2)

        self.reset_btn = ttk.Button(btn_frame, text="重新开始", command=self._ai_reset)
        self.reset_btn.pack(pady=2)

        self.export_btn = ttk.Button(btn_frame, text="导出docx", command=self._ai_export, state=tk.DISABLED)
        self.export_btn.pack(pady=2)

        # 绑定回车键
        self.chat_input.bind("<Return>", lambda e: self._ai_chat_send())

        # ── 右侧：配置区 ──
        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame, weight=1)

        # LLM配置
        llm_frame = ttk.LabelFrame(right_frame, text="LLM配置", padding=10)
        llm_frame.pack(fill=tk.X, padx=5, pady=5)

        row1 = ttk.Frame(llm_frame)
        row1.pack(fill=tk.X, pady=2)
        ttk.Label(row1, text="提供商:", width=8).pack(side=tk.LEFT)
        ttk.Combobox(row1, textvariable=self.gen_provider, values=["openai", "anthropic", "ollama"], width=12).pack(side=tk.LEFT, padx=5)

        row2 = ttk.Frame(llm_frame)
        row2.pack(fill=tk.X, pady=2)
        ttk.Label(row2, text="API Key:", width=8).pack(side=tk.LEFT)
        ttk.Entry(row2, textvariable=self.gen_key, width=20, show="*").pack(side=tk.LEFT, padx=5)

        row3 = ttk.Frame(llm_frame)
        row3.pack(fill=tk.X, pady=2)
        ttk.Label(row3, text="模型:", width=8).pack(side=tk.LEFT)
        ttk.Entry(row3, textvariable=self.gen_model, width=20).pack(side=tk.LEFT, padx=5)

        # 文档类型
        doc_frame = ttk.LabelFrame(right_frame, text="文档设置", padding=10)
        doc_frame.pack(fill=tk.X, padx=5, pady=5)

        row4 = ttk.Frame(doc_frame)
        row4.pack(fill=tk.X, pady=2)
        ttk.Label(row4, text="类型:", width=8).pack(side=tk.LEFT)
        ttk.Entry(row4, textvariable=self.gen_doc_type, width=20).pack(side=tk.LEFT, padx=5)

        row5 = ttk.Frame(doc_frame)
        row5.pack(fill=tk.X, pady=2)
        ttk.Label(row5, text="模板:", width=8).pack(side=tk.LEFT)
        doc_templates = ["无"] + [f"{t['name']} - {t['description']}" for t in list_doc_templates()]
        ttk.Combobox(row5, textvariable=self.gen_template, values=doc_templates, width=20).pack(side=tk.LEFT, padx=5)

        # 状态显示
        status_frame = ttk.LabelFrame(right_frame, text="状态", padding=10)
        status_frame.pack(fill=tk.X, padx=5, pady=5)

        self.ai_status_label = ttk.Label(status_frame, text="就绪", wraplength=200, font=("Microsoft YaHei", 9))
        self.ai_status_label.pack(fill=tk.X)

        # 提示信息
        tip_frame = ttk.LabelFrame(right_frame, text="使用提示", padding=10)
        tip_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        tips = """1. 输入文档描述，AI会自动识别类型并生成大纲

2. 确认大纲后，AI会逐节生成内容

3. 生成完成后点击"导出docx"下载

4. 支持多轮对话修改文档内容

5. 回复"重新开始"可开始新文档"""
        ttk.Label(tip_frame, text=tips, wraplength=200, justify=tk.LEFT, font=("Microsoft YaHei", 9)).pack(fill=tk.BOTH, expand=True)

    # ── Tab 5: 规则检查 ──────────────────────────────────────

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

    # ── Tab 6: 使用说明 ──────────────────────────────────────

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

【格式工作台】
- 上传论文后点击"扫描论文"查看文档结构
- 点击"预览矫正计划"可在应用前查看影响范围
- 配置样式后点击"应用到全部同类元素"执行矫正
- 可从模板库选择已有模板，或将样本保存为个人模板

【报告中心】
- 查看历史处理记录，包含质量评分和耗时
- 点击"查看详情"查看完整的矫正报告

【封面生成】
填写论文信息，点击"生成封面"自动生成标准封面页。

【AI文档生成（对话式）】
1. 输入文档描述（如"写一个项目可行性报告"）
2. AI自动识别文档类型并生成大纲
3. 点击"确认大纲"后，AI逐节生成内容
4. 生成完成后点击"导出docx"下载
5. 支持多轮对话修改文档内容

支持的文档类型：报告、公文、合同、方案、论文、会议纪要等。

【规则检查】
拖拽论文文件和 YAML 规则文件，点击"开始检查"。

【命令行用法】
  python run.py                              # 启动选择器
  python main.py -f paper.docx --score       # 命令行模式
  python main.py --generate "写一个可行性报告"  # AI生成文档
  python gui.py                              # 直接启动 Web GUI

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{CONTACT_INFO}"""

        text.insert(tk.END, help_content)
        text.config(state=tk.DISABLED)

    # ── 核心功能 ──────────────────────────────────────────────

    def _set_buttons_state(self, state):
        """启用/禁用处理按钮"""
        self.correct_btn.config(state=state)
        self.batch_btn.config(state=state)

    def _run_correct(self):
        """执行单个论文矫正"""
        paper = self.paper_path.get().strip()
        if not paper:
            messagebox.showwarning("提示", "请先选择或拖拽论文文件")
            return

        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, "正在处理，请稍候...\n")
        self._set_buttons_state("disabled")
        self.root.update()

        def do_work():
            try:
                result = self._process_single(paper)
                self.root.after(0, lambda: self._show_result(result))
            except Exception:
                logging.getLogger(__name__).exception("处理失败")
                self.root.after(0, lambda: self._show_result("处理失败，请检查输入文件是否正确。"))
            finally:
                self.root.after(0, lambda: self._set_buttons_state("normal"))

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
        self._set_buttons_state("disabled")
        self.root.update()

        def do_work():
            results = []
            for i, paper in enumerate(files, 1):
                self.root.after(0, lambda p=paper, idx=i: self._show_result(
                    f"[{idx}/{len(files)}] 正在处理: {Path(p).name}...\n"))
                try:
                    result = self._process_single(paper)
                    results.append(f"[{i}/{len(files)}] {Path(paper).name}\n{result}\n")
                except Exception:
                    logging.getLogger(__name__).exception("批量处理失败")
                    results.append(f"[{i}/{len(files)}] {Path(paper).name} - 处理失败，请检查文件格式\n")

            final = "\n" + "=" * 60 + "\n批量处理完成\n" + "=" * 60 + "\n\n" + "\n".join(results)
            self.root.after(0, lambda: self._show_result(final))
            self.root.after(0, lambda: self._set_buttons_state("normal"))

        threading.Thread(target=do_work, daemon=True).start()

    def _process_single(self, paper):  # noqa: C901
        """处理单个文件，返回结果文本"""
        from .infra.path_security import ALLOWED_INPUT_EXTENSIONS
        from .infra.path_security import validate_input_path as _vip

        # 预校验论文路径
        try:
            _vip(paper, ALLOWED_INPUT_EXTENSIONS)
        except (ValueError, FileNotFoundError) as e:
            return f"输入文件校验失败: {e}"

        cfg = self.config_path.get().strip() or CONFIG_PATH
        try:
            c = PaperFormatCorrector(cfg)
        except Exception as e:
            return f"配置加载失败: {e}"

        # 覆盖模板文件
        tpl = self.template_path_var.get().strip()
        if tpl:
            from .infra.path_security import validate_input_path
            tpl = str(validate_input_path(tpl, {".docx"}))
            c.template_path = tpl
            c.corrector = FormatCorrector(tpl, c.config)

        # 应用需求文档
        req = self.requirement_path.get().strip()
        if req:
            c.apply_requirement(req)

        # 格式转换
        input_path = Path(paper)
        converter = FileConverter()
        tmp_dir = None
        try:
            if converter.needs_conversion(str(input_path)):
                tmp_dir = Path(tempfile.mkdtemp())
                converted = converter.convert(str(input_path), str(tmp_dir))
                input_path = Path(converted)
        except Exception:
            self._log.exception("格式转换失败")

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
        if self.export_pdf.get():
            export_formats.append("pdf")
        if self.export_html.get():
            export_formats.append("html")
        if self.export_txt.get():
            export_formats.append("txt")
        if self.export_md.get():
            export_formats.append("md")

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
        if report.get("citation_style"):
            lines.append(f"\n检测到引用风格: {report['citation_style']}")
        if report.get("ref_issues"):
            lines.append(f"\n参考文献问题 ({len(report['ref_issues'])} 项):")
            for issue in report["ref_issues"]:
                lines.append(f"  - {issue}")
        if diff_path:
            lines.append(f"\n对比报告: {diff_path}")
        if score_report:
            lines.append(f"\n{score_report}")

        # 存储预览数据
        self._last_report = report
        self._last_diff_path = diff_path
        self._last_score_report = score_report

        # 保存处理历史
        try:
            quality_score = 0.0
            if self.do_score.get() and score_report:
                import re as _re
                _m = _re.search(r"总分[：:]\s*([\d.]+)", score_report)
                if _m:
                    quality_score = float(_m.group(1))
            TemplateRepository().save_processing_history(
                input_file=str(paper),
                output_file=str(output_path),
                template_used=self.wb_template_choice.get().split(" | ", 1)[0] if self.wb_template_choice.get() != "无（使用默认配置）" else "",
                quality_score=quality_score,
                total_elements=report.get("paragraphs_corrected", 0) + report.get("headings_fixed", 0) + report.get("body_fixed", 0),
                modified_elements=report.get("paragraphs_corrected", 0),
                report=report,
            )
        except Exception:
            logging.getLogger(__name__).exception("保存处理历史失败")

        # 清理临时转换目录
        if tmp_dir and tmp_dir.exists():
            shutil.rmtree(tmp_dir, ignore_errors=True)

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
        except Exception:
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
            tmp_dir = None
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
            except Exception:
                logging.getLogger(__name__).exception("规则检查失败")
                self.root.after(0, lambda: self._show_rule_result("检查失败，请检查输入文件是否正确。"))
            finally:
                if tmp_dir and tmp_dir.exists():
                    shutil.rmtree(tmp_dir, ignore_errors=True)

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

    # ── AI文档生成对话功能 ─────────────────────────────────────

    def _get_ai_generator(self):
        """获取或创建AI文档生成器"""
        from .parsers.ai_doc_generator import AIDocGenerator

        if self._ai_session is None:
            self._ai_session = AIDocGenerator(
                provider=self.gen_provider.get(),
                api_key=self.gen_key.get() or None,
                model=self.gen_model.get() or None,
            )
        return self._ai_session

    def _append_chat(self, role: str, content: str):
        """向聊天窗口追加消息"""
        self.chat_display.config(state=tk.NORMAL)

        if role == "user":
            self.chat_display.insert(tk.END, "\n你: ", "user_name")
        elif role == "assistant":
            self.chat_display.insert(tk.END, "\nAI: ", "ai_name")
        elif role == "system":
            self.chat_display.insert(tk.END, "\n[系统] ", "system_msg")

        self.chat_display.insert(tk.END, content + "\n")
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)

    def _update_status(self, text: str):
        """更新状态标签"""
        self.ai_status_label.config(text=text)

    def _ai_chat_send(self):
        """发送消息（在后台线程执行）"""
        message = self.chat_input.get("1.0", tk.END).strip()
        if not message:
            return

        self.chat_input.delete("1.0", tk.END)
        self._append_chat("user", message)
        self._update_status("正在处理...")

        # 禁用按钮
        self.send_btn.config(state=tk.DISABLED)
        self.confirm_btn.config(state=tk.DISABLED)

        def do_work():
            try:
                gen = self._get_ai_generator()

                if self._ai_outline is None:
                    # 首次对话，生成大纲
                    self.root.after(0, lambda: self._update_status("正在生成大纲..."))
                    outline = gen.generate_outline(message, self.gen_doc_type.get() or "通用文档")
                    self._ai_outline = outline

                    # 格式化大纲显示
                    outline_text = f"识别的文档类型: {outline.get('doc_type', '未知')}\n"
                    outline_text += f"文档标题: {outline.get('title', '未知')}\n"
                    outline_text += f"摘要: {outline.get('abstract', '')}\n\n"
                    outline_text += "大纲结构:\n"

                    for item in outline.get("outline", []):
                        item_type = item.get("type", "")
                        title = item.get("title", "")
                        desc = item.get("description", "")
                        indent = "  " if "2" in item_type or "3" in item_type else ""
                        outline_text += f"{indent}{title}\n"
                        if desc:
                            outline_text += f"{indent}  ({desc})\n"

                    outline_text += '\n请确认大纲是否满意，点击"确认大纲"开始生成内容。'
                    self.root.after(0, lambda: self._append_chat("assistant", outline_text))
                    self.root.after(0, lambda: self._update_status("大纲已生成，请确认"))
                    self.root.after(0, lambda: self.confirm_btn.config(state=tk.NORMAL))

                elif self._ai_structure is None:
                    # 大纲已生成，等待确认或修改
                    if "确认" in message or "ok" in message.lower() or "开始" in message:
                        self._ai_confirm_outline()
                    else:
                        self.root.after(0, lambda: self._append_chat("assistant",
                            '请告诉我具体需要调整的内容，或者点击"确认大纲"开始生成。'))
                        self.root.after(0, lambda: self.confirm_btn.config(state=tk.NORMAL))
                else:
                    # 文档已生成
                    self.root.after(0, lambda: self._append_chat("assistant",
                        '文档已生成完成。\n你可以：\n1. 点击"导出docx"下载\n2. 告诉我需要修改的内容\n3. 回复"重新开始"生成新文档'))
                    self.root.after(0, lambda: self.export_btn.config(state=tk.NORMAL))

            except Exception:
                logging.getLogger(__name__).exception("AI处理失败")
                self.root.after(0, lambda: self._append_chat("system", "出错了: 请检查API配置后重试。"))
                self.root.after(0, lambda: self._update_status("错误"))
            finally:
                self.root.after(0, lambda: self.send_btn.config(state=tk.NORMAL))

        threading.Thread(target=do_work, daemon=True).start()

    def _ai_confirm_outline(self):
        """确认大纲并开始生成内容"""
        if self._ai_outline is None:
            messagebox.showinfo("提示", "请先生成大纲")
            return

        self._append_chat("user", "确认大纲")
        self._update_status("正在生成文档内容...")
        self.send_btn.config(state=tk.DISABLED)
        self.confirm_btn.config(state=tk.DISABLED)

        def do_work():
            try:
                gen = self._get_ai_generator()
                gen.confirm_outline(True)

                self.root.after(0, lambda: self._append_chat("system", "大纲已确认，开始逐节生成内容..."))

                # 生成完整文档
                structure = gen.generate_structure(
                    self._ai_outline.get("title", ""),
                    self.gen_doc_type.get() or "通用文档",
                )
                self._ai_structure = structure

                # 生成预览
                doc_gen = DocGenerator()
                preview = doc_gen.generate_preview(structure)

                self.root.after(0, lambda: self._append_chat("assistant",
                    f'文档生成完成！\n\n预览:\n{preview[:500]}...\n\n点击"导出docx"下载。'))
                self.root.after(0, lambda: self._update_status("文档生成完成"))
                self.root.after(0, lambda: self.export_btn.config(state=tk.NORMAL))

            except Exception:
                logging.getLogger(__name__).exception("AI文档生成失败")
                self.root.after(0, lambda: self._append_chat("system", "生成失败: 请检查API配置后重试。"))
                self.root.after(0, lambda: self._update_status("错误"))
            finally:
                self.root.after(0, lambda: self.send_btn.config(state=tk.NORMAL))

        threading.Thread(target=do_work, daemon=True).start()

    def _ai_export(self):
        """导出文档为docx"""
        if self._ai_structure is None:
            messagebox.showinfo("提示", "文档尚未生成完成")
            return

        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / "generated_document.docx"

        try:
            doc_gen = DocGenerator()
            doc_gen.generate(self._ai_structure, str(output_path))
            self._append_chat("system", f"文档已导出: {output_path}")
            self._update_status(f"导出成功: {output_path}")
            messagebox.showinfo("成功", f"文档已导出:\n{output_path.resolve()}")
        except Exception as e:
            logging.getLogger(__name__).exception("导出失败")
            messagebox.showerror("错误", f"导出失败: {str(e)}")

    def _ai_reset(self):
        """重置AI会话"""
        self._ai_session = None
        self._ai_outline = None
        self._ai_structure = None

        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.delete("1.0", tk.END)
        self.chat_display.config(state=tk.DISABLED)

        self.confirm_btn.config(state=tk.DISABLED)
        self.export_btn.config(state=tk.DISABLED)
        self._update_status("会话已重置，可以开始新文档")

    def run(self):
        """启动应用"""
        self.root.mainloop()


def main():
    app = PaperFormatDesktopApp()
    app.run()


if __name__ == "__main__":
    main()
