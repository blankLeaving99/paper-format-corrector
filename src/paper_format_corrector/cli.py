"""论文格式矫正工具 - CLI 入口"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .app import PaperFormatCorrector
from .core.format_corrector import FormatCorrector
from .infra.preset_loader import get_preset_choices, format_preset_list


def main() -> None:
    preset_choices = get_preset_choices()

    parser = argparse.ArgumentParser(
        description="论文格式自动矫正工具 v3.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  基础用法:
    python -m paper_format_corrector                         # 批量处理 input/ 目录
    python -m paper_format_corrector -f paper.docx           # 处理单个文件
    python -m paper_format_corrector -f paper.docx -o out    # 指定输出路径

  格式预设（SCI/IEEE/Nature/APA/毕业论文）:
    python -m paper_format_corrector --list-presets          # 列出所有预设
    python -m paper_format_corrector --preset ieee -f paper.docx
    python -m paper_format_corrector --preset nature -f paper.docx
    python -m paper_format_corrector --preset chinese_thesis -f paper.docx

  需求文档驱动:
    python -m paper_format_corrector -r requirement.txt -f paper.docx
    python -m paper_format_corrector -r requirement.docx     # 批量处理

  质量检查:
    python -m paper_format_corrector -f paper.docx --score
    python -m paper_format_corrector -f paper.docx --diff
    python -m paper_format_corrector -f paper.docx --rules rules.yaml

  封面生成:
    python -m paper_format_corrector --cover title="论文题目" author="张三"

  LLM智能解析:
    python -m paper_format_corrector -r requirement.txt -f paper.docx --llm

  模板/导出:
    python -m paper_format_corrector --extract
    python -m paper_format_corrector -f paper.docx --format pdf html

  GUI界面:
    python -m paper_format_corrector --gui          # Web GUI（浏览器）
    python -m paper_format_corrector --desktop-gui   # 桌面 GUI（原生窗口）
        """,
    )

    # 基础参数
    parser.add_argument("-f", "--file", help="处理单个文件路径 (支持 .docx/.doc/.odt/.rtf/.pdf/.txt/.md)")
    parser.add_argument("-o", "--output", help="输出文件路径")
    parser.add_argument("-i", "--input-dir", default="input", help="输入目录（默认: input）")
    parser.add_argument("-d", "--output-dir", default="output", help="输出目录（默认: output）")
    parser.add_argument("-t", "--template", help="模板文件路径")
    parser.add_argument("--no-template", action="store_true", help="不使用模板，直接用配置规则矫正")
    parser.add_argument("-c", "--config", default="config/config.yaml", help="配置文件路径")

    # 格式预设
    parser.add_argument(
        "--preset",
        choices=preset_choices if preset_choices else None,
        help=f"格式预设: {', '.join(preset_choices)}",
    )
    parser.add_argument("--list-presets", action="store_true", help="列出所有可用的格式预设")

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
    parser.add_argument("--gui", action="store_true", help="启动Web GUI界面（浏览器）")
    parser.add_argument("--desktop-gui", action="store_true", help="启动桌面 GUI 界面")
    parser.add_argument("--extract", action="store_true", help="仅提取模板样式信息")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    args = parser.parse_args()

    print("=" * 60)
    print("  论文格式自动矫正工具 v3.0")
    print("=" * 60)

    for dir_name in ("template", "input", "output"):
        Path(dir_name).mkdir(exist_ok=True)

    corrector = PaperFormatCorrector(args.config, args.log_level)

    # 列出预设
    if args.list_presets:
        print(format_preset_list())
        return

    # 应用格式预设
    if args.preset:
        print(f"\n应用格式预设: {args.preset}")
        corrector.apply_preset(args.preset)
        print()

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
    if args.no_template:
        corrector.template_path = ""
        corrector.corrector = FormatCorrector("", corrector.config)
    elif args.template:
        corrector.template_path = args.template
        corrector.corrector = FormatCorrector(args.template, corrector.config)

    # 启动GUI
    if args.gui:
        try:
            from .gui import main as gui_main
            gui_main()
        except ImportError:
            print("Web GUI需要安装gradio: pip install gradio")
        return

    if args.desktop_gui:
        from .desktop_gui import main as desktop_main
        desktop_main()
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
        if args.output:
            from .infra.path_security import validate_output_path, ALLOWED_OUTPUT_EXTENSIONS
            validate_output_path(args.output, ALLOWED_OUTPUT_EXTENSIONS)
        corrector.process_single(args.file, args.output, args.format, args.score, args.diff)
    else:
        if not Path(corrector.template_path).exists():
            corrector.logger.warning(f"模板文件不存在 ({corrector.template_path})")
        corrector.process_directory(args.input_dir, args.output_dir, args.format, args.score)

    print("\n处理完成！")


if __name__ == "__main__":
    main()
