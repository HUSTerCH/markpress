import argparse
import sys
from pathlib import Path


def _cmd_convert(args):
    from markpress.converter import convert_markdown_file

    input_path = Path(args.input).resolve()
    if not input_path.exists() or not input_path.is_file():
        print(f"[Fatal] 找不到输入文件: {input_path}", file=sys.stderr)
        sys.exit(1)

    if args.output:
        output_path = Path(args.output).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        output_path = input_path.with_suffix(".pdf")

    try:
        print(f"[MarkPress] 正在编译: {input_path.name} -> {output_path.name}")
        convert_markdown_file(str(input_path), str(output_path), args.theme)
        print(f"[MarkPress] 编译成功！输出路径: {output_path}")
        sys.exit(0)
    except Exception as e:
        print(f"\n[CRITICAL] 引擎宕机: {str(e)}", file=sys.stderr)
        if args.debug:
            raise e
        print("提示: 添加 --debug 参数查看详细堆栈追踪。", file=sys.stderr)
        sys.exit(1)


def _cmd_serve(args):
    from markpress.server import serve
    print(f"[MarkPress] Web 界面已启动 → http://{args.host}:{args.port}")
    serve(host=args.host, port=args.port)


def main():
    parser = argparse.ArgumentParser(
        prog="markpress",
        description="MarkPress: Markdown 转 PDF 渲染器",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command")

    # ---------- convert 子命令 ----------
    p_convert = subparsers.add_parser(
        "convert",
        help="将 Markdown 文件转换为 PDF",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    p_convert.add_argument("input", type=str, help="输入的 Markdown 文件路径")
    p_convert.add_argument(
        "-o", "--output", type=str,
        help="输出的 PDF 文件路径（默认: 与源文件同级同名）",
    )
    p_convert.add_argument(
        "-t", "--theme", type=str, default="academic",
        help="排版主题 (默认: academic，可选: lark / github / vue)",
    )
    p_convert.add_argument(
        "--debug", action="store_true",
        help="开启 Debug 模式，打印完整堆栈追踪",
    )

    # ---------- serve 子命令 ----------
    p_serve = subparsers.add_parser(
        "serve",
        help="启动 Web 界面，在浏览器中转换 Markdown",
    )
    p_serve.add_argument(
        "--host", type=str, default="127.0.0.1",
        help="监听地址 (默认: 127.0.0.1)",
    )
    p_serve.add_argument(
        "--port", type=int, default=8080,
        help="监听端口 (默认: 8080)",
    )

    args = parser.parse_args()

    if args.command == "convert":
        _cmd_convert(args)
    elif args.command == "serve":
        _cmd_serve(args)
    else:
        # 无子命令时打印帮助
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
