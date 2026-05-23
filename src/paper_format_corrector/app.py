"""论文格式矫正主程序"""

from __future__ import annotations

import yaml
import copy
from pathlib import Path
from typing import Any

from .core.style_extractor import StyleExtractor
from .core.format_corrector import FormatCorrector
from .core.format_exporter import FormatExporter
from .core.file_converter import FileConverter
from .parsers.requirement_parser import RequirementParser
from .quality.quality_scorer import QualityScorer
from .quality.diff_reporter import DiffReporter
from .quality.rule_engine import RuleEngine
from .generators.cover_page_generator import CoverPageGenerator
from .infra.logger import Logger, ProgressBar
from .infra.preset_loader import load_preset, list_presets, format_preset_list
from .infra.path_security import validate_input_path, validate_output_path, ALLOWED_INPUT_EXTENSIONS
from .infra.compat import check_dependencies

try:
    from .parsers.llm_parser import LLMParser, llm_parse_to_config
    HAS_LLM = True
except ImportError:
    HAS_LLM = False


class PaperFormatCorrector:
    """论文格式矫正主程序"""

    def __init__(self, config_path: str = "config/config.yaml", log_level: str = "INFO") -> None:
        with open(config_path, "r", encoding="utf-8") as f:
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
        llm_provider: str = "openai",
        llm_api_key: str | None = None,
        llm_model: str | None = None,
    ) -> None:
        """解析需求文档并应用到配置"""
        # 校验需求文档路径
        validate_input_path(requirement_path, ALLOWED_INPUT_EXTENSIONS)
        req_config = None

        # 尝试LLM解析
        if use_llm and HAS_LLM:
            try:
                from .parsers.llm_parser import LLMParser, llm_parse_to_config
                llm = LLMParser(provider=llm_provider, api_key=llm_api_key, model=llm_model)
                doc_text = Path(requirement_path).read_text(encoding="utf-8")
                llm_result = llm.parse(doc_text)
                if llm_result:
                    req_config = llm_parse_to_config(llm_result)
                    self.logger.info("LLM解析成功")
            except Exception as e:
                self.logger.warning(f"LLM解析失败，回退到正则解析: {e}")

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

        # 格式转换（如果需要）
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

        if output_file is None:
            output_path = Path("output") / f"formatted_{input_path.name}"
        else:
            output_path = Path(output_file)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        self.corrector.load_template_styles()

        # 保留原始副本用于diff
        orig_path = None
        if diff:
            import shutil
            orig_path = str(output_path) + ".orig.docx"
            shutil.copy2(str(input_path), orig_path)

        try:
            report = self.corrector.correct_document(str(input_path), str(output_path))
            self._print_report(input_path.name, report)

            # 导出其他格式
            if export_formats:
                self._export_formats(output_path, export_formats)

            # 质量评分
            if score:
                total, scores, issues = self.scorer.score(str(output_path))
                print(self.scorer.format_report(total, scores, issues))
                report["quality_score"] = total

            # 对比报告
            if diff and orig_path:
                diff_path = output_path.with_suffix(".diff.html")
                self.diff_reporter.generate_html_report(orig_path, str(output_path), str(diff_path))
                print(f"\n  对比报告已生成: {diff_path}")
                # 清理临时文件
                Path(orig_path).unlink(missing_ok=True)

            return report
        except Exception as e:
            self.logger.error(f"处理失败 {input_path.name}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def process_directory(
        self,
        input_dir: str = "input",
        output_dir: str = "output",
        export_formats: list[str] | None = None,
        score: bool = False,
    ) -> None:
        """批量处理目录"""
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        self.corrector.load_template_styles()

        input_path = Path(input_dir)
        converter = FileConverter()

        # 支持所有支持的格式
        doc_files = []
        for ext in FileConverter.SUPPORTED_INPUT_FORMATS:
            doc_files.extend(input_path.glob(f"*{ext}"))
        doc_files = sorted(doc_files, key=lambda f: f.name)

        if not doc_files:
            self.logger.warning(f"在 {input_dir} 目录下未找到支持的文档文件")
            return

        self.logger.info(f"找到 {len(doc_files)} 个文档需要处理")

        total_report = {
            "files_processed": 0, "files_failed": 0,
            "total_paragraphs": 0, "total_headings": 0, "total_body": 0,
            "all_ref_issues": [], "all_fig_table_issues": [],
        }

        progress = ProgressBar(len(doc_files), desc="Processing")

        for doc_file in doc_files:
            # 格式转换
            processing_file = doc_file
            if converter.needs_conversion(str(doc_file)):
                self.logger.info(f"  转换格式: {doc_file.name} ({doc_file.suffix} → .docx)")
                try:
                    converted_path = converter.convert(str(doc_file), output_dir)
                    processing_file = Path(converted_path)
                except Exception as e:
                    total_report["files_failed"] += 1
                    self.logger.error(f"格式转换失败 {doc_file.name}: {e}")
                    progress.update()
                    continue

            output_file = Path(output_dir) / f"formatted_{processing_file.name}"
            try:
                report = self.corrector.correct_document(str(processing_file), str(output_file))
                total_report["files_processed"] += 1
                total_report["total_paragraphs"] += report.get("paragraphs_corrected", 0)
                total_report["total_headings"] += report.get("headings_fixed", 0)
                total_report["total_body"] += report.get("body_fixed", 0)
                total_report["all_ref_issues"].extend(report.get("ref_issues", []))
                total_report["all_fig_table_issues"].extend(report.get("fig_table_issues", []))

                if export_formats:
                    self._export_formats(output_file, export_formats)

                if score:
                    total, _, _ = self.scorer.score(str(output_file))
                    self.logger.info(f"  {doc_file.name}: 质量评分 {total}/100")

            except Exception as e:
                total_report["files_failed"] += 1
                self.logger.error(f"处理失败 {doc_file.name}: {e}")

            progress.update()

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

    def _validate_config(self) -> None:
        """验证配置结构和值类型"""
        if not isinstance(self.config, dict):
            raise ValueError("配置文件格式错误：顶层必须是字典")

        margins = self.config.get("format_rules", {}).get("margins", {})
        for key in ("top", "bottom", "left", "right"):
            if key in margins and not isinstance(margins[key], (int, float)):
                raise ValueError(f"margins.{key} 必须是数字，当前值: {margins[key]}")

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

        print(f"\n页面边距:")
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
