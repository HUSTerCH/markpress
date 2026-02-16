import os
import tempfile

import mistune
from .core import MarkPressEngine


def convert_markdown_file(input_path: str, output_path: str, theme: str = "academic"):
    """
    读取 Markdown 文件，解析为 AST，驱动 Writer 生成 PDF。
    """
    # 1. 读取文件
    with open(input_path, "r", encoding="utf-8") as f:
        text = f.read()

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

    # 3. 获取 AST (Abstract Syntax Tree)
    # 这是一个由字典组成的列表，每个字典代表一个 Block (段落, 标题, 代码块等)
    ast = markdown(text)

    # 4. 初始化 PDF 引擎
    writer = MarkPressEngine(output_path, theme)

    # 5. 遍历 AST 并渲染
    _render_ast(writer, ast)

    # 6. 保存
    writer.save_pdf()
    writer.close_katex_render()
    # writer.try_trigger_autosave()


def _render_ast(writer: MarkPressEngine, tokens: list):
    """
    AST 遍历调度器 (Block Level)
    """
    for token in tokens:
        t_type = token.get('type')
        children = token.get('children')
        attrs = token.get('attrs', {})

        # --- 标题 (Heading) ---
        if t_type == 'heading':
            level = attrs.get('level', 1)
            text = _render_inline(writer, children)
            writer.add_heading(text, level=level)

        # --- 段落 (Paragraph) ---
        elif t_type == 'paragraph':
            text = _render_inline(writer, children)
            # 过滤掉空的图片段落（如果图片被单独处理了）
            if text.strip():
                writer.add_text(text)

        # --- 代码块 (Block Code) ---
        elif t_type == 'block_code':
            code = token.get('raw', '')
            info = attrs.get('info', '')  # 语言，例如 python
            writer.add_code(code, language=info)

        # --- 列表 (List) ---
        elif t_type == 'list':
            # print("识别到list，暂时跳过")
            ordered = attrs.get('ordered', False)
            list_items = _parse_list_items(writer, children)
            writer.add_list(list_items, is_ordered=ordered)

        # --- 表格 (Table) ---
        elif t_type == 'table':
            print("识别到table，暂时跳过")
            # table_data = _parse_table(children)
            # if table_data:
            #     writer.add_table(table_data)

        # --- 分隔线 (Thematic Break) ---
        elif t_type == 'thematic_break':
            writer.add_horizontal_rule()

        # --- 引用 (Blockquote) ---
        elif t_type == 'block_quote':
            # 1. 压栈：告诉 Writer 进入引用模式 (增加缩进/改变样式)
            writer.start_quote()

            # 2. 递归：把子元素（可能是 paragraph，也可能是更深层的 block_quote）
            #    再次扔给 _render_ast 处理
            _render_ast(writer, children)

            # 3. 弹栈：告诉 Writer 退出引用模式
            writer.end_quote()
        elif t_type == 'block_math':
            # 行间公式
            # print("行间公式，暂时跳过")
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

        if t_type == 'text':
            # 普通text，必须转义 XML 字符，防止 & < > 破坏 PDF 结构
            text = tok.get('raw', '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            result.append(text)
        elif t_type == 'inline_html':
            # 行内html
            result.append(tok.get('raw', ''))
        elif t_type == 'strong':
            # 加粗字体
            result.append(f"<b>{_render_inline(writer, tok.get('children'))}</b>")
        elif t_type == 'emphasis':
            # 斜体字体
            # ReportLab 的 Italic 需要字体支持，否则可能显示方框
            # 只要注册了 Italic 字体就可以用 <i>
            result.append(f"<i>{_render_inline(writer, tok.get('children'))}</i>")

        elif t_type == 'codespan':
            # 行内代码块，就是被``包裹的文字
            code = tok.get('raw', '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            # 给行内代码加个背景色需要高级设置，这里简单加粗或换字体
            result.append(f'<font face="Courier">{code}</font>')
        elif t_type == 'inline_math':
            # 行内公式，生成 <img/> 标签
            # 这里的 raw 就是 latex 源码
            try:
                latex = tok.get('raw', '')
                png_bytes, w, h = writer.katex_renderer.render_image(tok.get('raw', ''), is_block=False)
                if png_bytes:
                    # 走katex
                    fd, path = tempfile.mkstemp(suffix=".png")
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
        elif t_type == 'link':
            # 链接
            text = _render_inline(writer, tok.get('children'))
            href = tok.get('attrs', {}).get('url', '')
            # ReportLab 的超链接标签
            result.append(f'<a href="{href}" color="blue">{text}</a>')

        elif t_type == 'image':
            # 图片处理比较复杂，ReportLab 需要本地路径
            # 这里暂时只显示图片 Alt 文本，防止报错
            alt = tok.get('attrs', {}).get('alt', 'Image')
            result.append(f'[Image: {alt}]')

        elif t_type == 'softbreak':
            # 软换行
            result.append("")  # 移除
        elif t_type == 'linebreak':
            # 硬换行
            result.append("<br/>")  # 强制换行

    return "".join(result)


def _parse_list_items(writer, tokens) -> list:
    """
    将 mistune 的 list_item tokens 转换为 ['Item', ['SubItem'], 'Item'] 格式
    """
    result = []
    for tok in tokens:
        if tok['type'] == 'list_item':
            # list_item 的 children 可能包含 paragraph, text, 或者是嵌套的 list
            li_children = tok.get('children', [])

            # 1. 提取当前项的文本 (通常在第一个 paragraph 里)
            current_text = ""
            sub_list = None

            for child in li_children:
                if child['type'] == 'block_code':
                     # 列表里嵌代码块比较麻烦，这里简化处理，或者暂不支持
                     continue

                if child['type'] == 'list':
                    # 发现嵌套列表，递归解析
                    sub_list = _parse_list_items(writer, child['children'])
                else:
                    # 这是一个文本节点 (paragraph 或 text)
                    # 使用 _render_inline 获取 XML 文本
                    # 注意：如果是 paragraph，child['children'] 才是 inline tokens
                    if 'children' in child:
                         current_text += _render_inline(writer, child['children'])
                    elif 'raw' in child:
                         current_text += child['raw']

            # 2. 添加到结果
            if current_text:
                result.append(current_text)

            # 3. 如果有子列表，紧跟在文本后面添加
            if sub_list:
                result.append(sub_list)

    return result


def _parse_table(writer: MarkPressEngine, table_children: list) -> list:
    """
    辅助函数：解析表格
    """
    rows = []
    # table_head, table_body
    for section in table_children:
        if section.get('type') in ['table_head', 'table_body']:
            for row in section.get('children', []):
                current_row = []
                for cell in row.get('children', []):
                    # cell -> paragraph / text
                    # cell 的 children 里通常直接就是 text，或者 paragraph
                    # 简化处理：直接提取文本
                    # 注意：Mistune 3 的 table cell 结构可能比较深
                    cell_content = _render_inline(writer, cell.get('children', []))
                    current_row.append(cell_content)
                rows.append(current_row)
    return rows
