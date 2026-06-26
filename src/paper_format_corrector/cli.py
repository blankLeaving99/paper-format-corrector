"""论文格式矫正工具 - CLI 入口"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .app import PaperFormatCorrector
from .core.doc_generator import DocGenerator
from .core.format_corrector import FormatCorrector
from .infra.doc_template_loader import list_doc_templates, load_doc_template
from .infra.preset_loader import format_preset_list, get_preset_choices


def _handle_generate(args) -> None:
    """处理AI文档生成"""
    user_input = args.generate
    if not user_input:
        print("\n请输入文档描述（输入空行结束）：")
        lines = []
        while True:
            try:
                line = input()
                if not line:
                    break
                lines.append(line)
            except EOFError:
                break
        user_input = "\n".join(lines)

    if not user_input.strip():
        print("错误：未提供文档描述")
        sys.exit(1)

    print(f"\n文档描述: {user_input}")
    print(f"文档类型: {args.doc_type}")
    print()

    template_config = None
    if args.doc_template:
        try:
            template_config = load_doc_template(args.doc_template)
            print(f"使用模板: {args.doc_template}")
        except FileNotFoundError as e:
            print(f"警告: {e}")

    try:
        from .parsers.ai_doc_generator import AIDocGenerator
        ai_gen = AIDocGenerator(
            provider=args.gen_provider,
            api_key=args.gen_key,
            model=args.gen_model,
        )
    except Exception as e:
        print(f"错误: 无法创建AI生成器: {e}")
        sys.exit(1)

    if args.stream:
        # 流式模式：实时输出AI生成的内容
        print("正在调用AI生成文档内容（流式模式）...\n")

        try:
            print("=" * 60)
            print("AI生成内容（实时输出）:")
            print("=" * 60)

            # 流式生成完整文档结构
            for chunk in ai_gen.generate_structure_stream(user_input, args.doc_type):
                print(chunk, end="", flush=True)

            print("\n" + "=" * 60)
            print("AI生成完成！")

            # 获取最终结构
            structure = ai_gen.session.outline.get("structure", {})
            if not structure:
                # 如果outline中没有structure，尝试重新生成
                structure = ai_gen.generate_structure(user_input, args.doc_type)

        except Exception as e:
            print(f"\n错误: AI生成失败: {e}")
            sys.exit(1)

    else:
        # 非流式模式（向后兼容）
        print("正在调用AI生成文档内容...")
        try:
            structure = ai_gen.generate_structure(user_input, args.doc_type)
        except Exception as e:
            print(f"错误: AI生成失败: {e}")
            sys.exit(1)

        print("AI生成完成！")

    print("\n正在创建Word文档...")

    format_rules = template_config.get("format_rules", {}) if template_config else {}
    doc_gen = DocGenerator(format_rules)

    output_path = Path("output") / "generated_document.docx"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        doc_gen.generate(structure, str(output_path))
        print(f"\n文档已生成: {output_path.resolve()}")
        print(f"标题: {structure.get('title', '未命名')}")
        print(f"段落数: {len(structure.get('sections', []))}")
    except Exception as e:
        print(f"错误: 文档生成失败: {e}")
        sys.exit(1)


def _handle_interactive_chat(args) -> None:
    """处理交互式AI对话（新增功能）"""
    from .parsers.ai_doc_generator import AIDocGenerator

    try:
        ai_gen = AIDocGenerator(
            provider=args.gen_provider,
            api_key=args.gen_key,
            model=args.gen_model,
        )
    except Exception as e:
        print(f"错误: 无法创建AI生成器: {e}")
        sys.exit(1)

    print("=" * 60)
    print("  AI文档生成 - 交互式对话模式")
    print("=" * 60)
    print("输入文档描述开始对话，输入 'quit' 或 'exit' 退出")
    print("输入 'confirm' 确认大纲，输入 'reset' 重新开始")
    print()

    while True:
        try:
            user_input = input("你: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\n再见！")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("\n再见！")
            break
        if user_input.lower() == "reset":
            ai_gen.reset_session()
            print("[系统] 会话已重置\n")
            continue

        try:
            # 检查当前状态
            if ai_gen.session.outline is None:
                # 生成大纲
                print("\n[系统] 正在生成大纲...")
                outline = ai_gen.generate_outline(user_input, args.doc_type or "通用文档")

                print(f"\nAI: 识别的文档类型: {outline.get('doc_type', '未知')}")
                print(f"    文档标题: {outline.get('title', '未知')}")
                print(f"    摘要: {outline.get('abstract', '')}")
                print("\n    大纲结构:")
                for item in outline.get("outline", []):
                    item_type = item.get("type", "")
                    title = item.get("title", "")
                    desc = item.get("description", "")
                    indent = "      " if "2" in item_type or "3" in item_type else "    "
                    print(f"    {indent}{title}")
                    if desc:
                        print(f"    {indent}  ({desc})")
                print()
                print("[提示] 输入 'confirm' 确认大纲，或告诉我需要修改的地方")

            elif not ai_gen.session.outline.get("structure"):
                # 大纲已生成，等待确认
                if "confirm" in user_input.lower() or "确认" in user_input:
                    ai_gen.confirm_outline(True)
                    print("\n[系统] 大纲已确认，开始生成文档内容...\n")

                    structure = ai_gen.generate_structure(
                        ai_gen.session.outline.get("title", ""),
                        args.doc_type or "通用文档",
                    )
                    ai_gen.session.outline["structure"] = structure

                    # 生成预览
                    doc_gen = DocGenerator()
                    preview = doc_gen.generate_preview(structure)
                    print(f"AI: 文档生成完成！\n\n预览:\n{preview[:500]}...\n")

                    # 保存文件
                    output_path = Path("output") / "generated_document.docx"
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    doc_gen.generate(structure, str(output_path))
                    print(f"[系统] 文档已保存: {output_path.resolve()}")
                    print("[提示] 输入 'reset' 生成新文档，或告诉我需要修改的内容")
                else:
                    print("\nAI: 请告诉我需要调整的内容，或输入 'confirm' 确认大纲")

            else:
                # 文档已生成
                print("\nAI: 文档已生成完成。")
                print("    你可以：")
                print("    1. 输入 'reset' 生成新文档")
                print("    2. 告诉我需要修改的内容")
                print("    3. 输入 'quit' 退出")

        except Exception as e:
            print(f"\n错误: {e}")
            print("[提示] 请检查API配置后重试")


def main() -> None:
    """CLI 主入口"""
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

  AI文档生成:
    python -m paper_format_corrector --generate "写一个关于智慧城市的可行性报告"
    python -m paper_format_corrector --generate "写一个项目立项报告" --doc-type 报告
    python -m paper_format_corrector --generate "写一个劳动合同" --doc-type 合同
    python -m paper_format_corrector --generate --stream      # 流式输出模式
    python -m paper_format_corrector --chat                    # 交互式对话模式
    python -m paper_format_corrector --list-doc-templates

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

    # AI文档生成
    parser.add_argument("--generate", nargs="?", const="", help="AI生成文档: '描述文字' 或留空进入交互模式")
    parser.add_argument("--stream", action="store_true", help="流式输出AI生成内容")
    parser.add_argument("--chat", action="store_true", help="进入交互式AI对话模式")
    parser.add_argument("--doc-type", default="通用文档", help="文档类型（报告/公文/论文/合同等）")
    parser.add_argument("--doc-template", help="文档模板名称")
    parser.add_argument("--list-doc-templates", action="store_true", help="列出所有可用的文档模板")
    parser.add_argument("--gen-provider", default="openai", choices=["openai", "anthropic", "ollama"], help="AI生成使用的LLM提供商")
    parser.add_argument("--gen-key", help="AI生成使用的LLM API Key")
    parser.add_argument("--gen-model", help="AI生成使用的LLM模型名称")

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

    # 列出文档模板
    if args.list_doc_templates:
        templates = list_doc_templates()
        if not templates:
            print("未找到文档模板。")
            return
        print("\n可用的文档模板:")
        print("-" * 60)
        for t in templates:
            hints = ", ".join(t.get("doc_type_hints", [])[:3])
            print(f"  {t['name']:<25s} {t['description']}")
            if hints:
                print(f"  {'':25s} 适用类型: {hints}")
        print("-" * 60)
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
        try:
            from .desktop_gui import main as desktop_main
            desktop_main()
        except ImportError:
            print("桌面 GUI 需要安装 tkinterdnd2: pip install tkinterdnd2")
            sys.exit(1)
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
            from datetime import datetime
            now = datetime.now()
            metadata = {
                "title": "论文题目",
                "author": "作者姓名",
                "college": "学院名称",
                "major": "专业名称",
                "date": f"{now.year}年{now.month}月",
            }
        cover_path = Path("output") / "cover.docx"
        corrector.generate_cover(metadata, str(cover_path))
        return

    # 交互式AI对话模式
    if args.chat:
        _handle_interactive_chat(args)
        return

    # AI文档生成
    if args.generate is not None:
        _handle_generate(args)
        return

    # 自定义规则检查
    if args.rules and args.file:
        corrector.check_rules(args.file, rules_path=args.rules)
        return

    # 处理
    if args.file:
        if args.output:
            from .infra.path_security import ALLOWED_OUTPUT_EXTENSIONS, validate_output_path
            validate_output_path(args.output, ALLOWED_OUTPUT_EXTENSIONS)
        corrector.process_single(args.file, args.output, args.format, args.score, args.diff)
    else:
        if corrector.template_path and not Path(corrector.template_path).exists():
            corrector.logger.warning(f"模板文件不存在 ({corrector.template_path})")
        corrector.process_directory(args.input_dir, args.output_dir, args.format, args.score)

    print("\n处理完成！")


if __name__ == "__main__":
    main()
