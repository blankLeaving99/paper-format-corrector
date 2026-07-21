"""LaTeX 导出模块

将 DOCX 文件转换为 LaTeX (.tex) 格式。
优先使用 pandoc 进行高质量转换，不可用时降级为纯文本提取。
"""

import re
import shutil
import subprocess
from pathlib import Path


class LaTeXExporter:
    """DOCX → LaTeX 导出器"""

    # 支持的文档类
    DOCUMENT_CLASSES = ("article", "report", "book", "ctexart", "ctexrep", "ctexbook")

    # 中文相关宏包
    CTEX_PACKAGES = ("ctex", "xeCJK", "CJKutf8")

    def __init__(self, config=None):
        self.config = config or {}

    @staticmethod
    def _find_pandoc() -> str | None:
        """查找 pandoc 可执行文件路径"""
        pandoc = shutil.which("pandoc")
        if pandoc:
            return pandoc

        # 常见安装路径
        candidates = [
            r"C:\Program Files\Pandoc\pandoc.exe",
            "/usr/bin/pandoc",
            "/usr/local/bin/pandoc",
            "/opt/homebrew/bin/pandoc",
        ]
        for p in candidates:
            if Path(p).exists():
                return p
        return None

    @staticmethod
    def _detect_chinese(content: str) -> bool:
        """检测文本中是否包含中文字符"""
        return bool(re.search(r"[\u4e00-\u9fff]", content))

    def export(
        self,
        docx_path: str,
        output_path: str,
        template: str = None,
        document_class: str = None,
        extra_packages: list[str] = None,
    ) -> str:
        """将 DOCX 转换为 LaTeX 文件

        Args:
            docx_path: 输入 DOCX 文件路径
            output_path: 输出 .tex 文件路径
            template: 可选的 LaTeX 模板内容（注入到 preamble）
            document_class: 文档类（article/report/book/ctexart 等）
            extra_packages: 额外的 \\usepackage 命令列表

        Returns:
            生成的 .tex 文件路径
        """
        docx_path = Path(docx_path)
        output_path = Path(output_path)

        if not docx_path.exists():
            raise FileNotFoundError(f"DOCX 文件不存在: {docx_path}")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 读取 DOCX 内容用于中文检测
        content = self._extract_docx_text(str(docx_path))
        is_chinese = self._detect_chinese(content)

        # 优先使用 pandoc
        pandoc = self._find_pandoc()
        if pandoc:
            return self._export_via_pandoc(
                pandoc, docx_path, output_path,
                template=template,
                document_class=document_class,
                extra_packages=extra_packages,
                is_chinese=is_chinese,
            )

        # 降级：纯文本提取 + LaTeX 包装
        return self._export_fallback(
            content, output_path,
            template=template,
            document_class=document_class,
            extra_packages=extra_packages,
            is_chinese=is_chinese,
        )

    def _export_via_pandoc(
        self,
        pandoc: str,
        docx_path: Path,
        output_path: Path,
        template: str = None,
        document_class: str = None,
        extra_packages: list[str] = None,
        is_chinese: bool = False,
    ) -> str:
        """使用 pandoc 执行 DOCX → LaTeX 转换"""
        cmd = [
            pandoc,
            str(docx_path),
            "-o", str(output_path),
            "--from=docx",
            "--to=latex",
            "--standalone",
        ]

        # 设置文档类
        doc_class = document_class or ("ctexart" if is_chinese else "article")
        cmd.extend(["--variable", f"documentclass={doc_class}"])

        # 中文文档添加 ctex 支持
        if is_chinese and doc_class not in ("ctexart", "ctexrep", "ctexbook"):
            cmd.extend(["--variable", "CJKmainfont=true"])

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:
            raise RuntimeError(f"pandoc 转换失败: {result.stderr}")

        if not output_path.exists():
            raise RuntimeError("pandoc 转换完成但未找到输出文件")

        # 后处理：注入自定义模板或宏包
        if template or extra_packages or is_chinese:
            self._post_process_preamble(
                output_path, template, extra_packages, is_chinese, doc_class
            )

        return str(output_path)

    def _export_fallback(
        self,
        content: str,
        output_path: Path,
        template: str = None,
        document_class: str = None,
        extra_packages: list[str] = None,
        is_chinese: bool = False,
    ) -> str:
        """降级方案：从 DOCX 提取文本后用 LaTeX 模板包装"""
        doc_class = document_class or ("ctexart" if is_chinese else "article")

        # 构建 preamble
        preamble_lines = []
        preamble_lines.append(f"\\documentclass{{{doc_class}}}")

        # 中文支持宏包
        if is_chinese:
            if doc_class not in ("ctexart", "ctexrep", "ctexbook"):
                preamble_lines.append("\\usepackage{ctex}")

        # 常用宏包
        preamble_lines.extend([
            "\\usepackage[utf8]{inputenc}",
            "\\usepackage{geometry}",
            "\\usepackage{graphicx}",
            "\\usepackage{booktabs}",
            "\\usepackage{longtable}",
            "\\usepackage{hyperref}",
        ])

        # 额外宏包
        if extra_packages:
            preamble_lines.extend(extra_packages)

        # 自定义模板
        if template:
            preamble_lines.append(f"% Custom template\n{template}")

        # 组装完整文档
        tex_parts = [
            "\n".join(preamble_lines),
            "",
            "\\begin{document}",
            "",
            content.strip(),
            "",
            "\\end{document}",
            "",
        ]

        output_path.write_text("\n".join(tex_parts), encoding="utf-8")
        return str(output_path)

    def _post_process_preamble(
        self,
        tex_path: Path,
        template: str = None,
        extra_packages: list[str] = None,
        is_chinese: bool = False,
        document_class: str = "article",
    ):
        """后处理 pandoc 输出的 .tex 文件，注入自定义内容"""
        content = tex_path.read_text(encoding="utf-8")

        # 在 \begin{document} 前注入内容
        injections = []

        # 中文支持
        if is_chinese and document_class not in ("ctexart", "ctexrep", "ctexbook"):
            # 检查是否已有 ctex
            if "\\usepackage{ctex}" not in content and "\\usepackage[UTF8]{ctex}" not in content:
                injections.append("\\usepackage{ctex}")

        # 额外宏包
        if extra_packages:
            for pkg in extra_packages:
                if pkg not in content:
                    injections.append(pkg)

        # 自定义模板
        if template:
            injections.append(f"% Custom template\n{template}")

        if injections:
            injection_text = "\n".join(injections) + "\n"
            content = content.replace(
                "\\begin{document}",
                f"{injection_text}\\begin{{document}}",
                1,
            )
            tex_path.write_text(content, encoding="utf-8")

    @staticmethod
    def _extract_docx_text(docx_path: str) -> str:
        """从 DOCX 提取纯文本（用于中文检测）"""
        try:
            from docx import Document
            doc = Document(docx_path)
            return "\n".join(p.text for p in doc.paragraphs)
        except ImportError:
            # 无法读取 docx 时返回空字符串
            return ""
