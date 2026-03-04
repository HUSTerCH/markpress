import argparse
import sys
from pathlib import Path
from markpress.converter import convert_markdown_file


def main():
    parser = argparse.ArgumentParser(
        description="MarkPress: Markdown 转 PDF 渲染器",
        formatter_class=argparse.RawTextHelpFormatter
    )

    # 必填参数：输入文件
    parser.add_argument(
        "input",
        type=str,
        help="输入的 Markdown 文件路径"
    )

    # 可选参数：输出文件
    parser.add_argument(
        "-o", "--output",
        type=str,
        help="输出的 PDF 文件路径。若不指定，则在源文件同级目录生成同名 PDF"
    )

    # 可选参数：主题配置
    parser.add_argument(
        "-t", "--theme",
        type=str,
        default="academic",
        help="指定排版主题配置 (默认: academic)"
    )

    # 调试开关
    parser.add_argument(
        "--debug",
        action="store_true",
        help="开启 Debug 模式，打印完整堆栈追踪并保留临时 AST 数据"
    )

    args = parser.parse_args()

    # 1. 物理路径严格校验
    input_path = Path(args.input).resolve()
    if not input_path.exists() or not input_path.is_file():
        print(f"[Fatal] 找不到输入文件: {input_path}", file=sys.stderr)
        sys.exit(1)

    # 2. 输出路径自动推导
    if args.output:
        output_path = Path(args.output).resolve()
        # 确保输出目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        output_path = input_path.with_suffix(".pdf")

    # 3. 执行核心管线与异常隔离
    try:
        print(f"[MarkPress] 正在编译: {input_path.name} -> {output_path.name}")

        # 此处可扩展：根据 args.theme 加载对应的 Config
        # config = load_config(args.theme)

        convert_markdown_file(str(input_path), str(output_path),args.theme)

        print(f"[MarkPress] 编译成功！输出路径: {output_path}")
        sys.exit(0)

    except Exception as e:
        print(f"\n[CRITICAL] 引擎宕机: {str(e)}", file=sys.stderr)
        # 只有在 --debug 模式下才向终端喷吐丑陋的 Python 堆栈追踪
        if args.debug:
            raise e
        else:
            print("提示: 添加 --debug 参数查看详细堆栈追踪。", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()