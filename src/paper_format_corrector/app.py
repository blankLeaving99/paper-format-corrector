"""论文格式矫正主程序

并行处理架构说明:
- 多文档并行: process_directory 使用 ProcessPoolExecutor，每个文档在独立进程中处理，
  各进程拥有独立的 FormatCorrector 实例和 lxml 文档树，无共享状态。
- 单文档内串行: 单个文档内的段落格式化、表格处理、图片处理等步骤必须串行执行，
  因为 python-docx/lxml 的底层 C 库不支持并发写入同一文档树。
- 后处理并行: correct_document 完成后的质量评分、对比报告、格式导出互不依赖，
  使用 ThreadPoolExecutor 并行执行。

GPU 加速说明:
- 本工具的核心工作是 XML 文档树的解析与修改（正则匹配 + DOM 操作），
  属于 CPU 密集型但非矩阵运算型任务，GPU 加速无显著收益。
- LLM API 调用（需求文档解析）属于网络 I/O 密集型，瓶颈在网络延迟而非计算。
- 若未来引入本地 ML 模型（如基于 Transformer 的段落分类器），可考虑 GPU 加速。
"""

from __future__ import annotations

import copy
import os
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import yaml

from .adapters.word.file_converter import FileConverter
from .adapters.word.file_formatter import FormatCorrector
from .adapters.word.format_exporter import FormatExporter
from .adapters.word.docx_adapter import StyleExtractor
from .adapters.word.cover_generator import CoverPageGenerator
from .adapters.compat import check_dependencies
from .adapters.logger import Logger, ProgressBar
from .adapters.path_security import ALLOWED_INPUT_EXTENSIONS, validate_input_path
from .adapters.preset_loader import load_preset
from .core.document.requirement_parser import RequirementParser
from .core.quality.diff_reporter import DiffReporter
from .core.quality.quality_scorer import QualityScorer
from .core.quality.rule_engine import RuleEngine

try:
    from importlib.util import find_spec as _find_spec
    HAS_LLM = _find_spec("paper_format_corrector.core.document.llm_parser") is not None
except ImportError:
    HAS_LLM = False


# ---------------------------------------------------------------------------
# 独立函数：可供 ProcessPoolExecutor 调用（可 pickle）
# ---------------------------------------------------------------------------

def _process_one_file(
    args: tuple[str, str, str, dict, bool, bool, list[str] | None],
) -> dict[str, Any]:
    """在子进程中处理单个文档。

    每个子进程创建独立的 FormatCorrector 实例，避免 lxml 并发写入问题。

    Args:
        args: (input_file, output_file, template_path, config,
               score, diff, export_formats)

    Returns:
        处理报告字典，失败时返回包含 error 键的字典。
    """
    input_file, output_file, template_path, config, score, diff, export_formats = args

    from .adapters.word.file_converter import FileConverter
    from .adapters.word.file_formatter import FormatCorrector
    from .adapters.word.format_exporter import FormatExporter

    try:
        input_path = Path(input_file)

        # 格式转换
        converter = FileConverter()
        if converter.needs_conversion(str(input_path)):
            converted_path = converter.convert(str(input_path), str(input_path.parent))
            input_path = Path(converted_path)

        corrector = FormatCorrector(template_path, config)
        report = corrector.correct_document(str(input_path), output_file)

        # 并行执行后处理（评分、导出、对比）
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = {}

            if export_formats:
                exporter = FormatExporter(config)
                futures["export"] = pool.submit(
                    _export_formats_parallel, exporter, Path(output_file), export_formats
                )

            if score:
                from .core.quality.quality_scorer import QualityScorer
                scorer = QualityScorer(config)
                futures["score"] = pool.submit(scorer.score, output_file)

            if diff:
                futures["diff"] = pool.submit(
                    _generate_diff, input_path, Path(output_file)
                )

            for name, future in futures.items():
                try:
                    result = future.result()
                    if name == "score":
                        total, _, _ = result
                        report["quality_score"] = total
                    elif name == "diff":
                        report["diff_path"] = result
                except Exception:
                    pass  # 后处理失败不影响主报告

        return report

    except Exception as e:
        return {"error": str(e), "file": input_file}


def _export_formats_parallel(exporter: FormatExporter, docx_path: Path, formats: list[str]) -> list[str]:
    """并行导出多种格式，返回成功导出的格式列表。"""
    exported = []
    for fmt in formats:
        fmt = fmt.lower().strip(".")
        if fmt in ("docx", "doc"):
            continue
        if fmt == "markdown":
            fmt = "md"
        out_path = docx_path.with_suffix(f".{fmt}")
        try:
            exporter.export(str(docx_path), str(out_path), fmt)
            exported.append(fmt)
        except Exception:
            pass
    return exported


def _generate_diff(orig_path: Path, output_path: Path) -> str | None:
    """生成对比报告，返回 diff 文件路径。"""
    from .core.quality.diff_reporter import DiffReporter
    diff_path = output_path.with_suffix(".diff.html")
    reporter = DiffReporter()
    reporter.generate_html_report(str(orig_path), str(output_path), str(diff_path))
    return str(diff_path)


class PaperFormatCorrector:
    """论文格式矫正主程序"""

    def __init__(self, config_path: str = "config/config.yaml", log_level: str = "INFO") -> None:
        with open(config_path, encoding="utf-8") as f:
            self.config = yaml.safe_load(f) or {}

        self._validate_config()
        self.template_path = self.config.get("template", {}).get("path", "")
        self.corrector = FormatCorrector(self.template_path, self.config)
        self.exporter = FormatExporter(self.config)
        self.scorer = QualityScorer(self.config)
        self.diff_reporter = DiffReporter()
        self.rule_engine = RuleEngine()
        self.logger = Logger(level=log_level)

        # 检查依赖兼容性
        for warning in check_dependencies():
            if "[ERROR]" in warning:
                self.logger.error(warning)
            else:
                self.logger.warning(warning)

    def apply_preset(self, preset_name: str) -> None:
        """Load and apply a format preset (e.g., 'ieee', 'nature', 'chinese_thesis')."""
        preset_config = load_preset(preset_name)
        self.config = self._merge_config(self.config, preset_config)
        self.corrector = FormatCorrector(self.template_path, self.config)
        self.scorer = QualityScorer(self.config)
        self.logger.info(f"已应用格式预设: {preset_name}")

    def apply_requirement(
        self,
        requirement_path: str,
        use_llm: bool = False,
        use_offline_parser: bool = False,
        llm_provider: str = "openai",
        llm_api_key: str | None = None,
        llm_model: str | None = None,
    ) -> None:
        """解析需求文档并应用到配置

        Args:
            requirement_path: 需求文档路径
            use_llm: 是否使用 LLM 解析
            use_offline_parser: 是否使用离线规则解析器（无需 LLM API）
            llm_provider: LLM 提供商
            llm_api_key: LLM API 密钥
            llm_model: LLM 模型名
        """
        # 校验需求文档路径
        validate_input_path(requirement_path, ALLOWED_INPUT_EXTENSIONS)
        req_config = None

        # 尝试LLM解析
        if use_llm and HAS_LLM:
            try:
                from .core.document.llm_parser import LLMParser, llm_parse_to_config
                llm = LLMParser(provider=llm_provider, api_key=llm_api_key, model=llm_model)
                doc_text = Path(requirement_path).read_text(encoding="utf-8")
                llm_result = llm.parse(doc_text)
                if llm_result:
                    req_config = llm_parse_to_config(llm_result)
                    self.logger.info("LLM解析成功")
            except Exception as e:
                self.logger.warning(f"LLM解析失败，回退到正则解析: {e}")

        # 使用离线规则解析器（推荐的离线方案）
        if req_config is None and use_offline_parser:
            try:
                from .core.document.rule_parser import parse_requirement_file
                req_config = parse_requirement_file(requirement_path)
                self.logger.info("离线规则解析成功")
            except Exception as e:
                self.logger.warning(f"离线规则解析失败，回退到基础解析: {e}")

        # 正则解析（默认或LLM失败时）
        if req_config is None:
            parser = RequirementParser()
            req_config = parser.parse(requirement_path)
            parser.print_parsed_rules()

        # 需求文档中指定的模板路径覆盖默认模板
        if "template" in req_config and "path" in req_config["template"]:
            tpl_path = req_config["template"]["path"]
            try:
                validate_input_path(tpl_path, {".docx"})
                self.template_path = tpl_path
                self.logger.info(f"使用需求文档指定的模板: {self.template_path}")
            except (ValueError, FileNotFoundError) as e:
                self.logger.warning(f"需求文档指定的模板路径无效，忽略: {e}")

        self.config = self._merge_config(self.config, req_config)
        self.corrector = FormatCorrector(self.template_path, self.config)
        self.scorer = QualityScorer(self.config)

    def _convert_input_file(self, input_path: Path) -> Path | None:
        """尝试转换文件格式，失败返回 None。"""
        converter = FileConverter()
        if converter.needs_conversion(str(input_path)):
            self.logger.info(f"正在转换文件格式: {input_path.suffix} → .docx")
            try:
                converted_path = converter.convert(str(input_path), str(input_path.parent))
                input_path = Path(converted_path)
                self.logger.info(f"格式转换完成: {input_path.name}")
            except Exception as e:
                self.logger.error(f"文件格式转换失败: {e}")
                return None
        return input_path

    def _resolve_output_path(self, input_path: Path, output_file: str | None) -> Path:
        """根据输入和输出参数确定最终输出路径。"""
        if output_file is None:
            output_path = Path("output") / f"formatted_{input_path.name}"
        else:
            output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        return output_path

    def _backup_for_diff(self, input_path: Path, output_path: Path) -> str | None:
        """为 diff 保留原始副本，返回副本路径。"""
        import shutil
        orig_path = str(output_path) + ".orig.docx"
        shutil.copy2(str(input_path), orig_path)
        return orig_path

    def _run_post_processing(
        self,
        report: dict,
        output_path: Path,
        export_formats: list[str] | None,
        score: bool,
        diff: bool,
        orig_path: str | None,
    ) -> None:
        """并行执行后处理：评分、导出、对比。"""
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = {}

            if export_formats:
                futures["export"] = pool.submit(
                    self._export_formats, output_path, export_formats
                )

            if score:
                futures["score"] = pool.submit(
                    self.scorer.score, str(output_path)
                )

            if diff and orig_path:
                futures["diff"] = pool.submit(
                    self._generate_diff_report, orig_path, str(output_path)
                )

            for name, future in futures.items():
                try:
                    result = future.result()
                    if name == "score":
                        total, scores, issues = result
                        print(self.scorer.format_report(total, scores, issues))
                        report["quality_score"] = total
                    elif name == "diff":
                        print(f"\n  对比报告已生成: {result}")
                except Exception as e:
                    self.logger.warning(f"后处理 {name} 失败: {e}")

    def process_single(
        self,
        input_file: str,
        output_file: str | None = None,
        export_formats: list[str] | None = None,
        score: bool = False,
        diff: bool = False,
    ) -> dict[str, Any] | None:
        """处理单个文件"""
        try:
            input_path = validate_input_path(input_file, ALLOWED_INPUT_EXTENSIONS)
        except (ValueError, FileNotFoundError) as e:
            self.logger.error(str(e))
            return None

        converted = self._convert_input_file(input_path)
        if converted is None:
            return None
        input_path = converted

        output_path = self._resolve_output_path(input_path, output_file)

        # 保留原始副本用于diff
        orig_path = None
        if diff:
            orig_path = self._backup_for_diff(input_path, output_path)

        try:
            report = self.corrector.correct_document(str(input_path), str(output_path))
            self._print_report(input_path.name, report)

            self._run_post_processing(report, output_path, export_formats, score, diff, orig_path)

            return report
        except Exception as e:
            self.logger.error(f"处理失败 {input_path.name}: {e}")
            self.logger.debug("详细错误信息", exc_info=True)
            return None
        finally:
            # 确保清理临时文件
            if orig_path:
                Path(orig_path).unlink(missing_ok=True)

    def _generate_diff_report(self, orig_path: str, output_path: str) -> str:
        """生成对比报告，返回 diff 文件路径。"""
        diff_path = Path(output_path).with_suffix(".diff.html")
        self.diff_reporter.generate_html_report(orig_path, output_path, str(diff_path))
        return str(diff_path)

    def _collect_doc_files(self, input_dir: str) -> list[Path]:
        """收集目录下所有支持格式的文档文件。"""
        input_path = Path(input_dir)
        doc_files = []
        for ext in FileConverter.SUPPORTED_INPUT_FORMATS:
            doc_files.extend(input_path.glob(f"*{ext}"))
        return sorted(doc_files, key=lambda f: f.name)

    def _build_task_list(
        self,
        doc_files: list[Path],
        output_dir: str,
        score: bool,
        export_formats: list[str] | None,
    ) -> list[tuple]:
        """构建多进程处理任务列表。"""
        tasks = []
        converter = FileConverter()
        for doc_file in doc_files:
            processing_file = doc_file
            if converter.needs_conversion(str(doc_file)):
                try:
                    converted_path = converter.convert(str(doc_file), output_dir)
                    processing_file = Path(converted_path)
                except Exception as e:
                    self.logger.error(f"格式转换失败 {doc_file.name}: {e}")
                    continue

            output_file = str(Path(output_dir) / f"formatted_{processing_file.name}")
            tasks.append((
                str(processing_file), output_file, self.template_path,
                self.config, score, False, export_formats,
            ))
        return tasks

    def _process_results(
        self,
        future_to_input: dict,
        total_report: dict,
        score: bool,
        progress: ProgressBar,
    ) -> None:
        """收集并汇总多进程处理结果。"""
        for future in as_completed(future_to_input):
            input_file = future_to_input[future]
            try:
                report = future.result()
                if "error" in report:
                    total_report["files_failed"] += 1
                    self.logger.error(f"处理失败 {Path(input_file).name}: {report['error']}")
                else:
                    total_report["files_processed"] += 1
                    total_report["total_paragraphs"] += report.get("paragraphs_corrected", 0)
                    total_report["total_headings"] += report.get("headings_fixed", 0)
                    total_report["total_body"] += report.get("body_fixed", 0)
                    total_report["all_ref_issues"].extend(report.get("ref_issues", []))
                    total_report["all_fig_table_issues"].extend(report.get("fig_table_issues", []))

                    if score and "quality_score" in report:
                        self.logger.info(f"  {Path(input_file).name}: 质量评分 {report['quality_score']}/100")
            except Exception as e:
                total_report["files_failed"] += 1
                self.logger.error(f"处理失败 {Path(input_file).name}: {e}")

            progress.update()

    def process_directory(
        self,
        input_dir: str = "input",
        output_dir: str = "output",
        export_formats: list[str] | None = None,
        score: bool = False,
        max_workers: int | None = None,
    ) -> None:
        """批量处理目录，支持多进程并行。

        Args:
            input_dir: 输入目录
            output_dir: 输出目录
            export_formats: 导出格式列表
            score: 是否进行质量评分
            max_workers: 最大并行进程数，默认为 CPU 核心数
        """
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        doc_files = self._collect_doc_files(input_dir)

        if not doc_files:
            self.logger.warning(f"在 {input_dir} 目录下未找到支持的文档文件")
            return

        if max_workers is None:
            max_workers = min(len(doc_files), os.cpu_count() or 4)

        self.logger.info(f"找到 {len(doc_files)} 个文档需要处理 (并行度: {max_workers})")

        total_report = {
            "files_processed": 0, "files_failed": 0,
            "total_paragraphs": 0, "total_headings": 0, "total_body": 0,
            "all_ref_issues": [], "all_fig_table_issues": [],
        }

        tasks = self._build_task_list(doc_files, output_dir, score, export_formats)

        if not tasks:
            self.logger.warning("所有文件格式转换失败")
            return

        # 多进程并行处理
        progress = ProgressBar(len(tasks), desc="Processing")

        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            future_to_input = {
                executor.submit(_process_one_file, task): task[0]
                for task in tasks
            }

            self._process_results(future_to_input, total_report, score, progress)

        progress.finish()
        self._print_summary(total_report)

    def generate_cover(self, metadata: dict[str, str], output_path: str, template: str = "standard") -> None:
        """生成封面页"""
        generator = CoverPageGenerator(self.config)
        generator.generate(metadata, output_path, template)
        self.logger.info(f"封面已生成: {output_path}")

    def check_rules(
        self,
        doc_path: str,
        rules_path: str | None = None,
        rules_list: list[dict] | None = None,
    ) -> list:
        """执行自定义规则检查"""
        from docx import Document
        doc = Document(str(doc_path))

        if rules_path:
            self.rule_engine.load_rules(rules_path)
        elif rules_list:
            self.rule_engine.load_rules_dict(rules_list)

        results = self.rule_engine.check(doc, self.config)
        print(self.rule_engine.format_report(results))
        return results

    def _export_formats(self, docx_path: Path, formats: list[str]) -> None:
        docx_path = Path(docx_path)
        for fmt in formats:
            fmt = fmt.lower().strip(".")
            if fmt in ("docx", "doc"):
                continue
            if fmt == "markdown":
                fmt = "md"
            out_path = docx_path.with_suffix(f".{fmt}")
            try:
                result = self.exporter.export(str(docx_path), str(out_path), fmt)
                self.logger.info(f"  已导出: {result}")
            except Exception as e:
                self.logger.warning(f"  导出 {fmt} 失败: {e}")

    def _validate_margins(self, margins: dict) -> None:
        """验证边距配置"""
        for key in ("top", "bottom", "left", "right"):
            if key in margins and not isinstance(margins[key], (int, float)):
                raise ValueError(f"margins.{key} 必须是数字，当前值: {margins[key]}")
            if key in margins and not (0.1 <= margins[key] <= 15):
                raise ValueError(f"margins.{key} 值不合理: {margins[key]}cm，应在 0.1~15 之间")

    def _validate_body_text(self, body: dict) -> None:
        """验证正文配置"""
        fs = body.get("font_size")
        if fs is not None and not isinstance(fs, (int, float)):
            raise ValueError(f"body_text.font_size 必须是数字，当前值: {fs}")
        if fs is not None and not (5 <= fs <= 72):
            raise ValueError(f"body_text.font_size 值不合理: {fs}pt，应在 5~72 之间")

    def _validate_headings(self, headings: dict) -> None:
        """验证标题配置"""
        for hk, hv in headings.items():
            if not isinstance(hv, dict):
                raise ValueError(f"headings.{hk} 必须是字典")
            hfs = hv.get("font_size")
            if hfs is not None and not isinstance(hfs, (int, float)):
                raise ValueError(f"headings.{hk}.font_size 必须是数字")

    def _validate_config(self) -> None:
        """验证配置结构和值类型"""
        if not isinstance(self.config, dict):
            raise ValueError("配置文件格式错误：顶层必须是字典")

        format_rules = self.config.get("format_rules", {})
        if not isinstance(format_rules, dict):
            raise ValueError("format_rules 必须是字典")

        margins = format_rules.get("margins", {})
        self._validate_margins(margins)

        body = format_rules.get("body_text", {})
        if body:
            self._validate_body_text(body)

        headings = format_rules.get("headings", {})
        if isinstance(headings, dict):
            self._validate_headings(headings)

    def _merge_config(self, base: dict, override: dict) -> dict:
        result = copy.deepcopy(base)
        for key, value in override.items():
            if key.startswith("_"):
                continue
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = copy.deepcopy(value)
        return result

    def extract_template_info(self) -> None:
        if not Path(self.template_path).is_file():
            print(f"模板文件不存在: {self.template_path}")
            return
        extractor = StyleExtractor(self.template_path)
        styles = extractor.extract_all_styles()
        margins = extractor.extract_page_margins()

        print("=" * 60)
        print("模板样式信息")
        print("=" * 60)
        target_styles = ["Normal", "Heading 1", "Heading 2", "Heading 3", "heading1", "heading2", "heading3"]
        for style_name, style_info in styles.items():
            if style_name in target_styles:
                print(f"\n  样式: {style_name}")
                print(f"    字体: {style_info['font_name']}")
                print(f"    字号: {style_info['font_size']}pt")
                print(f"    加粗: {style_info['bold']}")
                print(f"    对齐: {style_info['alignment']}")
                print(f"    行距: {style_info['line_spacing']}")

        print("\n页面边距:")
        print(f"  上: {margins['top']:.2f}cm  下: {margins['bottom']:.2f}cm")
        print(f"  左: {margins['left']:.2f}cm  右: {margins['right']:.2f}cm")
        print("=" * 60)

    def _print_report(self, filename, report):
        print(f"\n{'=' * 60}")
        print(f"处理报告: {filename}")
        print(f"{'=' * 60}")
        print(f"  矫正段落数: {report['paragraphs_corrected']}")
        print(f"  标题矫正:   {report['headings_fixed']}")
        print(f"  正文矫正:   {report['body_fixed']}")
        if report.get("tables_formatted"):
            print(f"  表格格式化: {report['tables_formatted']}")
        if report.get("images_centered"):
            print(f"  图片居中:   {report['images_centered']}")

        if report.get("fig_table_issues"):
            print(f"\n  图表编号修正 ({len(report['fig_table_issues'])} 项):")
            for issue in report["fig_table_issues"]:
                print(f"    - {issue}")
        if report.get("citation_style"):
            print(f"\n  检测到引用风格: {report['citation_style']}")
        if report.get("ref_issues"):
            print(f"\n  参考文献问题 ({len(report['ref_issues'])} 项):")
            for issue in report["ref_issues"]:
                print(f"    - {issue}")

    def _print_summary(self, report):
        print(f"\n{'=' * 60}")
        print("批量处理汇总")
        print(f"{'=' * 60}")
        print(f"  成功处理: {report['files_processed']} 个文件")
        if report["files_failed"]:
            print(f"  处理失败: {report['files_failed']} 个文件")
        print(f"  矫正段落: {report['total_paragraphs']}")
        print(f"  标题矫正: {report['total_headings']}")
        print(f"  正文矫正: {report['total_body']}")
