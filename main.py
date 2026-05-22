import argparse
import sys
import yaml
import copy
from pathlib import Path

from style_extractor import StyleExtractor
from format_corrector import FormatCorrector
from format_exporter import FormatExporter
from requirement_parser import RequirementParser
from quality_scorer import QualityScorer
from diff_reporter import DiffReporter
from rule_engine import RuleEngine
from cover_page_generator import CoverPageGenerator
from logger import Logger, ProgressBar

try:
    from llm_parser import LLMParser, llm_parse_to_config
    HAS_LLM = True
except ImportError:
    HAS_LLM = False


class PaperFormatCorrector:
    """论文格式矫正主程序"""

    def __init__(self, config_path="config.yaml", log_level="INFO"):
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        self.template_path = self.config["template"]["path"]
        self.corrector = FormatCorrector(self.template_path, self.config)
        self.exporter = FormatExporter()
        self.scorer = QualityScorer(self.config)
        self.diff_reporter = DiffReporter()
        self.rule_engine = RuleEngine()
        self.logger = Logger(level=log_level)

    def apply_requirement(self, requirement_path, use_llm=False, llm_provider="openai", llm_api_key=None, llm_model=None):
        """解析需求文档并应用到配置"""
        req_config = None

        # 尝试LLM解析
        if use_llm and HAS_LLM:
            try:
                from llm_parser import LLMParser, llm_parse_to_config
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

        self.config = self._merge_config(self.config, req_config)
        self.corrector = FormatCorrector(self.template_path, self.config)
        self.scorer = QualityScorer(self.config)

    def process_single(self, input_file, output_file=None, export_formats=None, score=False, diff=False):
        """处理单个文件"""
        input_path = Path(input_file)
        if not input_path.exists():
            self.logger.error(f"文件不存在: {input_file}")
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

    def process_directory(self, input_dir="input", output_dir="output", export_formats=None, score=False):
        """批量处理目录"""
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        self.corrector.load_template_styles()

        input_path = Path(input_dir)
        docx_files = sorted(
            list(input_path.glob("*.docx")) + list(input_path.glob("*.doc")),
            key=lambda f: f.name,
        )

        if not docx_files:
            self.logger.warning(f"在 {input_dir} 目录下未找到Word文档")
            return

        self.logger.info(f"找到 {len(docx_files)} 个文档需要处理")

        total_report = {
            "files_processed": 0, "files_failed": 0,
            "total_paragraphs": 0, "total_headings": 0, "total_body": 0,
            "all_ref_issues": [], "all_fig_table_issues": [],
        }

        progress = ProgressBar(len(docx_files), desc="Processing")

        for doc_file in docx_files:
            output_file = Path(output_dir) / f"formatted_{doc_file.name}"
            try:
                report = self.corrector.correct_document(str(doc_file), str(output_file))
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

    def generate_cover(self, metadata, output_path, template="standard"):
        """生成封面页"""
        generator = CoverPageGenerator(self.config)
        generator.generate(metadata, output_path, template)
        self.logger.info(f"封面已生成: {output_path}")

    def check_rules(self, doc_path, rules_path=None, rules_list=None):
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

    def _export_formats(self, docx_path, formats):
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

    def _merge_config(self, base, override):
        result = copy.deepcopy(base)
        for key, value in override.items():
            if key.startswith("_"):
                continue
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = copy.deepcopy(value)
        return result

    def extract_template_info(self):
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


def main():
    parser = argparse.ArgumentParser(
        description="论文格式自动矫正工具 v3.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  基础用法:
    python main.py                                    # 批量处理 input/ 目录
    python main.py -f paper.docx                      # 处理单个文件
    python main.py -f paper.docx -o out.docx          # 指定输出路径

  需求文档驱动:
    python main.py -r requirement.txt -f paper.docx   # 根据需求文档矫正
    python main.py -r requirement.docx                # 批量处理

  质量检查:
    python main.py -f paper.docx --score              # 矫正并评分
    python main.py -f paper.docx --diff               # 生成对比报告
    python main.py -f paper.docx --rules rules.yaml   # 自定义规则检查

  封面生成:
    python main.py --cover title="论文题目" author="张三"   # 生成封面

  LLM智能解析:
    python main.py -r requirement.txt -f paper.docx --llm  # 用LLM理解复杂需求

  模板/导出:
    python main.py --extract                          # 查看模板信息
    python main.py -f paper.docx --format pdf html    # 导出多格式
    python main.py --template t.docx                  # 使用指定模板

  GUI界面:
    python gui.py                                     # 启动Web界面
        """,
    )

    # 基础参数
    parser.add_argument("-f", "--file", help="处理单个文件路径")
    parser.add_argument("-o", "--output", help="输出文件路径")
    parser.add_argument("-i", "--input-dir", default="input", help="输入目录（默认: input）")
    parser.add_argument("-d", "--output-dir", default="output", help="输出目录（默认: output）")
    parser.add_argument("-t", "--template", help="模板文件路径")
    parser.add_argument("-c", "--config", default="config.yaml", help="配置文件路径")

    # 需求文档
    parser.add_argument("-r", "--requirement", help="需求文档路径（.docx/.txt/.md）")

    # LLM
    parser.add_argument("--llm", action="store_true", help="使用LLM智能解析需求文档")
    parser.add_argument("--llm-provider", default="openai", choices=["openai", "anthropic", "ollama"], help="LLM提供商")
    parser.add_argument("--llm-key", help="LLM API Key (也可用环境变量)")
    parser.add_argument("--llm-model", help="LLM模型名称")

    # 导出
    parser.add_argument("--format", nargs="+", help="额外导出格式: pdf html txt md")

    # 质量检查
    parser.add_argument("--score", action="store_true", help="输出格式质量评分")
    parser.add_argument("--diff", action="store_true", help="生成矫正前后对比HTML报告")
    parser.add_argument("--rules", help="自定义规则文件路径 (YAML)")

    # 封面生成
    parser.add_argument("--cover", nargs="*", help="生成封面，参数: key=value")

    # 其他
    parser.add_argument("--gui", action="store_true", help="启动Web GUI界面")
    parser.add_argument("--extract", action="store_true", help="仅提取模板样式信息")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    args = parser.parse_args()

    print("=" * 60)
    print("  论文格式自动矫正工具 v3.0")
    print("=" * 60)

    for dir_name in ("template", "input", "output"):
        Path(dir_name).mkdir(exist_ok=True)

    corrector = PaperFormatCorrector(args.config, args.log_level)

    # 需求文档
    if args.requirement:
        print(f"\n解析需求文档: {args.requirement}")
        corrector.apply_requirement(
            args.requirement,
            use_llm=args.llm,
            llm_provider=args.llm_provider,
            llm_api_key=args.llm_key,
            llm_model=args.llm_model,
        )
        print()

    # 模板覆盖
    if args.template:
        corrector.template_path = args.template
        corrector.corrector = FormatCorrector(args.template, corrector.config)

    # 启动GUI
    if args.gui:
        try:
            from gui import main as gui_main
            gui_main()
        except ImportError:
            print("GUI需要安装gradio: pip install gradio")
        return

    # 仅提取模板信息
    if args.extract:
        corrector.extract_template_info()
        return

    # 封面生成
    if args.cover is not None:
        metadata = {}
        for item in args.cover:
            if "=" in item:
                k, v = item.split("=", 1)
                metadata[k] = v
        if not metadata:
            metadata = {
                "title": "论文题目",
                "author": "作者姓名",
                "college": "学院名称",
                "major": "专业名称",
                "date": "2024年6月",
            }
        cover_path = Path("output") / "cover.docx"
        corrector.generate_cover(metadata, str(cover_path))
        return

    # 自定义规则检查
    if args.rules and args.file:
        corrector.check_rules(args.file, rules_path=args.rules)
        return

    # 处理
    if args.file:
        corrector.process_single(args.file, args.output, args.format, args.score, args.diff)
    else:
        if not Path(corrector.template_path).exists():
            corrector.logger.warning(f"模板文件不存在 ({corrector.template_path})")
        corrector.process_directory(args.input_dir, args.output_dir, args.format, args.score)

    print("\n处理完成！")


if __name__ == "__main__":
    main()
