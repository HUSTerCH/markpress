import os
import tempfile
import mistune
from .core import MarkPressEngine
from .utils import APP_TMP


def convert_markdown_file(input_path: str, output_path: str, theme: str = "academic"):
    """
    读取 Markdown 文件，解析为 AST，驱动 Writer 生成 PDF。
    """
    with open(input_path, "r", encoding="utf-8") as f:
        text = f.read()

    # 输入文件的目录，用于解析相对路径
    base_dir = os.path.dirname(os.path.abspath(input_path))

    # 初始化 Mistune
    markdown = mistune.create_markdown(
        renderer=None,  # 做解析，不是渲染
        plugins=[
            'speedup',
            'strikethrough',
            'mark',
            'insert',
            'superscript',
            'subscript',
            'footnotes',
            'table',
            'url',
            'abbr',
            'def_list',
            'math',
            'ruby',
            'task_lists',
            'spoiler'
        ]
    )

    # 获取 AST (Abstract Syntax Tree)，这是一个由字典组成的列表，每个字典代表一个 Block (段落, 标题, 代码块等)
    ast = markdown(text)

    # 初始化 PDF 引擎
    writer = MarkPressEngine(output_path, theme)

    # 遍历 AST 并渲染
    _render_ast(writer, ast, base_dir)

    # 保存并关闭katex引擎
    writer.save_pdf()
    writer.close_katex_render()


def _render_ast(writer: MarkPressEngine, tokens: list, base_dir: str = "."):
    """
    AST 遍历调度器 (Block Level)
    :param writer: PDF 引擎
    :param tokens: AST tokens
    :param base_dir: 基础目录，用于解析相对路径
    """
    for token in tokens:
        t_type = token.get('type')
        children = token.get('children')
        attrs = token.get('attrs', {})

        # 标题 (Heading)
        if t_type == 'heading':
            level = attrs.get('level', 1)
            text = _render_inline(writer, children)
            writer.add_heading(text, level=level)

        # 段落 (Paragraph)
        elif t_type == 'paragraph':
            # 检查是否只包含图片（独立图片段落）
            if len(children) == 1 and children[0].get('type') == 'image':
                img_attrs = children[0].get('attrs', {})
                img_url = img_attrs.get('url', '')
                img_alt = img_attrs.get('alt', '')
                # 处理相对路径
                if not os.path.isabs(img_url) and not img_url.startswith(('http://', 'https://')):
                    img_url = os.path.join(base_dir, img_url)
                writer.add_image(img_url, img_alt)
            else:
                text = _render_inline(writer,children)
                # 过滤掉空段落
                if text.strip():
                    writer.add_text(text)

        # 行间代码块 (Block Code)
        elif t_type == 'block_code':
            code = token.get('raw', '')
            info = attrs.get('info', '')  # 语言，例如 python
            writer.add_code(code, language=info)

        # 列表 (List)
        elif t_type == 'list':
            ordered = attrs.get('ordered', False)
            list_items = _parse_list_items(writer, children)
            writer.add_list(list_items, is_ordered=ordered)

        # 表格 (Table)
        elif t_type == 'table':
            table_data = _parse_table(writer, children, attrs)
            if table_data:
                writer.add_table(table_data)

        # 分隔线 (Thematic Break)
        elif t_type == 'thematic_break':
            writer.add_horizontal_rule()

        # 引用 (Blockquote)
        elif t_type == 'block_quote':
            # 压栈，告诉 Writer 进入引用模式 (增加缩进/改变样式)
            writer.start_quote()
            # 递归：把子元素（可能是 paragraph，也可能是更深层的 block_quote）再次扔给 _render_ast 处理
            _render_ast(writer, children, base_dir)
            # 弹栈：告诉 Writer 退出引用模式
            writer.end_quote()
        # 行间公式 (Block math)
        elif t_type == 'block_math':
            writer.add_formula(token.get('raw', ''))


def _render_inline(writer: MarkPressEngine, tokens: list) -> str:
    """
    将 Inline Tokens (Text, Strong, Link, Image) 转换为
    ReportLab 支持的 XML 字符串 (例如 <b>Text</b>)
    """
    if not tokens:
        return ""
    result = []
    for tok in tokens:
        t_type = tok.get('type')

        # 普通text，必须转义 XML 字符，防止 & < > 破坏 PDF 结构
        if t_type == 'text':
            text = tok.get('raw', '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            result.append(text)
        # 行内html
        elif t_type == 'inline_html':
            result.append(tok.get('raw', ''))
        # 加粗字体
        elif t_type == 'strong':
            result.append(f"<b>{_render_inline(writer, tok.get('children'))}</b>")
        # 斜体字体，需要有斜体字体支持
        elif t_type == 'emphasis':
            result.append(f"<i>{_render_inline(writer, tok.get('children'))}</i>")
        # 行内代码块，就是被``包裹的文字
        elif t_type == 'codespan':
            code = tok.get('raw', '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            # 给行内代码加个背景色需要高级设置，这里简单换字体
            result.append(f'<font face="{writer.config.fonts.code}">{code}</font>')
        # 行内公式，生成<img/> 标签
        elif t_type == 'inline_math':
            try:
                latex = tok.get('raw', '') # latex源码
                png_bytes, w, h = writer.katex_renderer.render_image(tok.get('raw', ''), is_block=False)
                if png_bytes:
                    # 走katex
                    fd, path = tempfile.mkstemp(suffix=".png",dir=APP_TMP)
                    os.write(fd, png_bytes)
                    os.close(fd)
                    # 计算下沉 (valign)
                    # KaTeX 的图片通常重心居中，行内公式需要下沉约 1/3 高度
                    valign = f"-{h * 0.3}"
                    xml_img = f'<img src="{path}" width="{w}" height="{h}" valign="{valign}"/>'
                else:
                    # 走matplot
                    xml_img = writer.formula_renderer.render_inline()
            except Exception:
                xml_img = f"<font color='red'>${latex}$</font>"
            result.append(xml_img)
        # 链接
        elif t_type == 'link':
            text = _render_inline(writer, tok.get('children'))
            href = tok.get('attrs', {}).get('url', '')
            result.append(f'<a href="{href}" color="blue">{text}</a>')
        # 行内图片
        elif t_type == 'image':
            # 图片处理比较复杂，ReportLab 需要本地路径
            # 这里暂时只显示图片 Alt 文本，防止报错
            alt = tok.get('attrs', {}).get('alt', 'Image')
            result.append(f'[Image: {alt}]')
        # 软换行，好像没遇到过
        elif t_type == 'softbreak':
            result.append("")
        # 硬换行，强制换行
        elif t_type == 'linebreak':
            result.append("<br/>")

    return "".join(result)


def _parse_list_items(writer, tokens) -> list:
    """
    解析列表的item
    将 mistune 的 list_item tokens 转换为 ['Item', ['SubItem'], 'Item'] 格式
    """
    result = []
    for tok in tokens:
        if tok['type'] == 'list_item':
            # list_item 的 children 可能包含 paragraph, text, 或者是嵌套的 list
            li_children = tok.get('children', [])
            # 提取当前项的文本 (通常在第一个 paragraph 里)
            current_text = ""
            sub_list = None

            for child in li_children:
                if child['type'] == 'block_code':
                     # 列表里嵌代码块比较麻烦，这里简化暂不支持（不过应该没有人会在列表放代码块）
                     continue
                # 嵌套列表，递归解析
                if child['type'] == 'list':
                    sub_list = _parse_list_items(writer, child['children'])
                else:
                    # 文本节点 (paragraph 或 text)，使用 _render_inline 获取 XML 文本
                    if 'children' in child:
                         current_text += _render_inline(writer, child['children'])
                    elif 'raw' in child:
                         current_text += child['raw']

            if current_text:
                result.append(current_text)

            # 如果有子列表，紧跟在文本后面添加
            if sub_list:
                result.append(sub_list)

    return result


def _parse_table(writer: MarkPressEngine, table_children: list, table_attrs: dict = None) -> dict:
    """
    解析 mistune 表格 AST，返回 {'header': [...], 'body': [[...], ...], 'aligns': [...]}
    """
    header = []
    body = []
    aligns = []

    for section in table_children:
        sec_type = section.get('type')
        if sec_type == 'table_head':
            # mistune 3 中 table_head 的 children 直接是 table_cell（无 table_row 包裹）
            for child in section.get('children', []):
                if child.get('type') == 'table_cell':
                    header.append(_render_inline(writer, child.get('children', [])))
                    aligns.append(child.get('attrs', {}).get('align'))
                elif child.get('type') == 'table_row':
                    for cell in child.get('children', []):
                        header.append(_render_inline(writer, cell.get('children', [])))
                        aligns.append(cell.get('attrs', {}).get('align'))

        elif sec_type == 'table_body':
            for row in section.get('children', []):
                current_row = []
                for cell in row.get('children', []):
                    current_row.append(_render_inline(writer, cell.get('children', [])))
                body.append(current_row)

    if not header and not body:
        return {}

    return {"header": header, "body": body, "aligns": aligns}
