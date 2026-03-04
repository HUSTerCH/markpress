import os
import re
import tempfile
from pprint import pprint

import mistune
from bs4 import BeautifulSoup
from .core import MarkPressEngine
from .utils.utils import APP_TMP, get_raw_text, slugify, strip_front_matter, optimize_ast_html_blocks


def convert_markdown_file(input_path: str, output_path: str, theme: str = "academic", config=None):
    """
    读取 Markdown 文件，解析为 AST，驱动 Writer 生成 PDF。
    config 为可选的 StyleConfig 对象，若传入则忽略 theme 参数直接使用该配置。
    """
    print(f"开始处理Markdown文件：{input_path}")
    with open(input_path, "r", encoding="utf-8") as f:
        text = f.read()
    clean_md = strip_front_matter(text)
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
    ast = markdown(clean_md)
    optimized_ast = optimize_ast_html_blocks(ast)

    # 初始化 PDF 引擎
    writer = MarkPressEngine(output_path, theme, config=config)

    # 遍历 AST 并渲染
    # _render_ast(writer, ast, base_dir)
    _render_ast(writer, optimized_ast, base_dir)

    # 保存并关闭katex引擎
    writer.save_pdf()
    writer.close_katex_render()
    print("Done.")


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
            # 1. 获取纯文本并生成目标 ID
            raw_text = get_raw_text(children)
            anchor_id = slugify(raw_text)

            # 2. 渲染带样式的 XML 内容
            xml_text = _render_inline(writer, children)

            # 3. [核心修复]：包裹锚点标签
            # 使用 <a name="..."> 整个包裹住标题文本
            # 这样既注册了书签目的地，又避免了产生空的 <a></a> 导致 CJK 换行崩溃
            text_with_anchor = f'<a name="{anchor_id}"/>{xml_text}'

            writer.add_heading(text_with_anchor, level=level)
            # text = _render_inline(writer, children)
            # writer.add_heading(text, level=level)

        # 段落 (Paragraph)
        elif t_type == 'paragraph':
            # 检测 mistune 未能解析的管道表格（不规则列数等情况）
            raw_text = get_raw_text(children)
            if '\n' in raw_text and '|' in raw_text:
                table_data = _try_parse_pipe_table(raw_text)
                if table_data:
                    writer.add_table(table_data)
                    continue

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
                text = _render_inline(writer, children)
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
            start_index = attrs.get('start', 1)
            list_items = _parse_list_items(writer, children)
            writer.add_list(list_items, is_ordered=ordered,start_index=start_index)

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
        elif t_type == 'block_html':
            raw_html = token.get('raw', '')
            # raw_html = raw_html.replace("</div>\n<div", "</div></div>\n<div<div")
            # raw_html_spilt = raw_html.split("</div>\n<div")
            # for raw_part in raw_html_spilt:
            # if raw_html.strip() != "":
            _parse_block_html(writer, raw_html.strip(), base_dir)


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
                latex = tok.get('raw', '')  # latex源码
                png_bytes, w, h = writer.katex_renderer.render_image(latex, is_block=False)
                if png_bytes:
                    # 走katex
                    fd, path = tempfile.mkstemp(suffix=".png", dir=APP_TMP)
                    os.write(fd, png_bytes)
                    os.close(fd)
                    # 计算下沉 (valign)
                    # KaTeX 的图片通常重心居中，行内公式需要下沉约 1/3 高度
                    valign = f"-{h * 0.3}"
                    xml_img = f'<img src="{path}" width="{w}" height="{h}" valign="{valign}"/>'
                else:
                    # 走matplot
                    xml_img = writer.formula_renderer.render_inline(latex)
            except Exception:
                xml_img = f"<font color='red'>${latex}$</font>"
            result.append(xml_img)
        # 链接
        elif t_type == 'link':
            text = _render_inline(writer, tok.get('children'))
            href = tok.get('attrs', {}).get('url', '')
            result.append(f'<a href="{href}" color="blue">{text}</a>')
        # 行内图片（如徽章、小图标等嵌在段落/链接里的图片）
        elif t_type == 'image':
            img_attrs = tok.get('attrs', {})
            src = img_attrs.get('url', '')
            alt = img_attrs.get('alt', 'Image')

            if '.svg' in src.lower() or 'shields.io' in src.lower():
                # SVG 徽章：通过浏览器光栅化
                img_path, w, h = writer.rasterize_svg(src)
                if img_path:
                    valign = f"-{h * 0.3}"
                    result.append(f'<img src="{img_path}" width="{w}" height="{h}" valign="{valign}"/>')
                else:
                    result.append(f'<font color="#666666">[{alt}]</font>')
            elif src.startswith(('http://', 'https://')):
                # 在线普通图片：下载后内联
                local_path = writer.image_renderer._download_image(src)
                if local_path:
                    from reportlab.platypus import Image as RLImage
                    try:
                        tmp_img = RLImage(local_path)
                        w, h = tmp_img.imageWidth * 0.75, tmp_img.imageHeight * 0.75
                        valign = f"-{h * 0.3}"
                        result.append(f'<img src="{local_path}" width="{w}" height="{h}" valign="{valign}"/>')
                    except Exception:
                        result.append(f'[{alt}]')
                else:
                    result.append(f'[{alt}]')
            else:
                result.append(f'[{alt}]')
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


def _try_parse_pipe_table(raw_text: str) -> dict:
    """尝试将原始文本解析为管道表格（应对 mistune 无法解析的非标准表格）"""
    lines = [l for l in raw_text.strip().split('\n') if l.strip()]
    if len(lines) < 2:
        return {}

    # 查找分隔线 (包含 |---|)
    sep_idx = -1
    for i, line in enumerate(lines):
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        if cells and all(re.match(r'^:?-+:?$', c) for c in cells if c):
            sep_idx = i
            break

    if sep_idx < 1:
        return {}

    def split_row(line):
        line = line.strip()
        if line.startswith('|'):
            line = line[1:]
        if line.endswith('|'):
            line = line[:-1]
        return [c.strip() for c in line.split('|')]

    header_cells = split_row(lines[sep_idx - 1])
    num_cols = len(header_cells)
    header = [c.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;') for c in header_cells]

    # 解析对齐方式
    sep_cells = split_row(lines[sep_idx])
    aligns = []
    for cell in sep_cells:
        cell = cell.strip()
        if cell.startswith(':') and cell.endswith(':'):
            aligns.append('center')
        elif cell.endswith(':'):
            aligns.append('right')
        else:
            aligns.append('left')
    while len(aligns) < num_cols:
        aligns.append('left')

    body = []
    for line in lines[sep_idx + 1:]:
        cells = split_row(line)
        cells = [c.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;') for c in cells]
        while len(cells) < num_cols:
            cells.append('')
        body.append(cells[:num_cols])

    if not header and not body:
        return {}
    return {"header": header, "body": body, "aligns": aligns}


def _extract_css_text_color(style: str):
    """从 CSS style 中提取文本颜色（排除 background-color）"""
    for part in style.split(';'):
        part = part.strip()
        if part.startswith('color:') or part.startswith('color :'):
            val = part.split(':', 1)[1].strip()
            if val.startswith('#'):
                return val
    return None


def _css_rgba_to_hex(rgba_str: str):
    """将 CSS rgba() 与白色背景混合后转换为十六进制颜色"""
    match = re.match(r'rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*([\d.]+))?\s*\)', rgba_str)
    if not match:
        return None
    r, g, b = int(match.group(1)), int(match.group(2)), int(match.group(3))
    a = float(match.group(4)) if match.group(4) else 1.0
    r = int(255 * (1 - a) + r * a)
    g = int(255 * (1 - a) + g * a)
    b = int(255 * (1 - a) + b * a)
    return f'#{r:02x}{g:02x}{b:02x}'


def _extract_css_bg_color(style: str):
    """从 CSS style 中提取背景颜色"""
    for part in style.split(';'):
        part = part.strip()
        if part.startswith('background:') or part.startswith('background-color:'):
            val = part.split(':', 1)[1].strip()
            if val.startswith('#'):
                return val
            if val.startswith('rgb'):
                return _css_rgba_to_hex(val)
    return None


def _parse_html_table(writer, table_tag) -> dict:
    """解析 HTML <table> 标签为表格数据字典，支持 colspan 和颜色提取"""
    header = []
    body = []
    aligns = []
    spans = []

    thead = table_tag.find('thead')
    tbody = table_tag.find('tbody')

    # 解析表头
    if thead:
        first_row = thead.find('tr')
        if first_row:
            for cell in first_row.find_all(['th', 'td']):
                text = cell.get_text(strip=True)
                text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                style = cell.get('style', '')
                if 'text-align:center' in style or 'text-align: center' in style:
                    aligns.append('center')
                elif 'text-align:right' in style or 'text-align: right' in style:
                    aligns.append('right')
                else:
                    aligns.append('left')
                text_color = _extract_css_text_color(style)
                if text_color:
                    text = f'<font color="{text_color}">{text}</font>'
                header.append(text)

    num_cols = len(header) if header else 0

    # 解析数据行
    rows_src = tbody.find_all('tr') if tbody else table_tag.find_all('tr')
    # 若无 thead，取第一行 <th> 作为表头
    if not thead and rows_src:
        first = rows_src[0]
        if first.find('th'):
            for th in first.find_all('th'):
                text = th.get_text(strip=True).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                header.append(text)
                aligns.append('left')
            num_cols = len(header)
            rows_src = rows_src[1:]

    row_backgrounds = {}

    for row_idx, tr in enumerate(rows_src):
        cells_tags = tr.find_all(['td', 'th'])
        row_data = []
        col_pos = 0
        data_row_idx = row_idx + (1 if header else 0)
        row_bg = None

        for cell in cells_tags:
            text = cell.get_text(strip=True)
            text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            colspan = int(cell.get('colspan', 1))

            style = cell.get('style', '')
            if 'font-weight:600' in style or 'font-weight: 600' in style or 'font-weight:bold' in style:
                text = f'<b>{text}</b>'
            text_color = _extract_css_text_color(style)
            if text_color:
                text = f'<font color="{text_color}">{text}</font>'
            bg_color = _extract_css_bg_color(style)
            if bg_color:
                row_bg = bg_color

            row_data.append(text)
            if colspan > 1:
                for _ in range(colspan - 1):
                    row_data.append('')
                spans.append(((col_pos, data_row_idx), (col_pos + colspan - 1, data_row_idx)))
            col_pos += colspan

        # 补齐列数
        if num_cols == 0 and row_data:
            num_cols = len(row_data)
        while len(row_data) < num_cols:
            row_data.append('')
        body.append(row_data[:num_cols] if num_cols > 0 else row_data)
        if row_bg:
            row_backgrounds[data_row_idx] = row_bg

    if not header and not body:
        return {}

    result = {"header": header, "body": body, "aligns": aligns}
    if spans:
        result["spans"] = spans
    if row_backgrounds:
        result["row_backgrounds"] = row_backgrounds
    return result


def _parse_block_html(writer, raw_html: str, base_dir: str = "."):
    # 1. 剔除注释
    html = re.sub(r'', '', raw_html, flags=re.DOTALL)
    if not html.strip():
        return

    soup = BeautifulSoup(html, 'html.parser')

    # 处理 HTML 表格（在其他 DOM 操作之前提取）
    for table_tag in soup.find_all('table'):
        table_data = _parse_html_table(writer, table_tag)
        if table_data:
            writer.add_table(table_data)
        table_tag.decompose()

    # 超链接上色与属性净化
    for a in soup.find_all('a'):
        # 扒光除了 href 和 name 之外的所有属性,比如 target="_blank", style="margin: 2px;", class="..." 都会导致崩溃
        safe_attrs = {}
        if a.get('href'):
            safe_attrs['href'] = a.get('href')
        if a.get('name'):
            safe_attrs['name'] = a.get('name')

        # 强制覆盖属性字典，物理超度一切非法属性
        a.attrs = safe_attrs

        if a.get('href'):
            # 如果 a 标签里面包着图片(比如徽章)，千万别加上划线
            if a.find('img'):
                continue

            # 给纯文本加上蓝色 <font color="blue">...</font>
            font_tag = soup.new_tag('font', color='blue')
            font_tag.extend(a.contents)
            a.clear()
            a.append(font_tag)
    # 4. 图片分拣 (内联徽章 vs 块级大图)
    valid_images = {}
    for img in soup.find_all('img'):
        src = img.get('src', '')
        alt = img.get('alt', '')

        if '.svg' in src.lower() or 'shields.io' in src.lower():
            img_path, w, h = writer.rasterize_svg(src)
            if img_path:
                new_img = soup.new_tag('img', src=img_path, width=str(w), height=str(h), valign="-5")
                if img.find_parent('a'):
                    img.replace_with(new_img)
                else:
                    marker = f"__IMG_{len(valid_images)}__"
                    valid_images[marker] = (src, alt)
                    img.replace_with(marker)
            else:
                new_tag = soup.new_tag('font', color='#666666')
                new_tag.string = f"[{alt}]"
                img.replace_with(new_tag)
        else:
            # 对非网络、非绝对路径的本地图片拼接 base_dir
            if src and not os.path.isabs(src) and not src.startswith(('http://', 'https://')):
                src = os.path.join(base_dir, src)
            marker = f"__IMG_{len(valid_images)}__"
            valid_images[marker] = (src, alt)
            img.replace_with(marker)

    # 5. 【核心修复：提取并保留格式属性与标题层级】
    for tag in soup.find_all(['div', 'p', 'center', 'right', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
        is_center = (tag.name == 'center' or tag.get('align') == 'center')
        is_right = (tag.name == 'right' or tag.get('align') == 'right')

        prefix = ""
        suffix = ""

        # 提取标题层级 (h1~h6)
        if tag.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            level = tag.name[1]
            prefix += f"__H{level}_START__"
            suffix = f"__H{level}_END__" + suffix

        # 提取对齐属性
        if is_center:
            prefix += "__CENTER_START__"
            suffix = "__CENTER_END__" + suffix
        elif is_right:
            prefix += "__RIGHT_START__"
            suffix = "__RIGHT_END__" + suffix

        # 放弃使用标签，改为插入极度安全的纯文本信标
        if prefix:
            tag.insert_before(prefix)
        if suffix:
            tag.insert_after(suffix)

        # 剥离原始标签
        tag.unwrap()

    for hr in soup.find_all('hr'):
        hr.replace_with('__HR__')

    clean_text = str(soup).replace('\n', ' ')

    # 6. 流式分发与渲染路由
    pattern = re.compile(r'(__HR__|__IMG_\d+__)')
    parts = pattern.split(clean_text)

    for part in parts:
        part = part.strip()
        if not part:
            continue

        if part == '__HR__':
            writer.add_horizontal_rule()
        elif part in valid_images:
            src, alt = valid_images[part]
            writer.add_image(image_path=src, alt_text=alt)
        else:
            # 解析对齐信标
            is_centered = False
            is_right = False
            heading_level = 0

            if '__CENTER_START__' in part or '__CENTER_END__' in part:
                is_centered = True
                part = part.replace('__CENTER_START__', '').replace('__CENTER_END__', '')
            if '__RIGHT_START__' in part or '__RIGHT_END__' in part:
                is_right = True
                part = part.replace('__RIGHT_START__', '').replace('__RIGHT_END__', '')

            # 解析标题信标
            for i in range(1, 7):
                if f'__H{i}_START__' in part or f'__H{i}_END__' in part:
                    heading_level = i
                    part = part.replace(f'__H{i}_START__', '').replace(f'__H{i}_END__', '')
                    break

            part = part.strip()
            if not part:
                continue

            # 决定对齐方式
            if is_centered:
                align = "center"
            elif is_right:
                align = "right"
            else:
                align = "left"

            # 路由分发机制
            if heading_level > 0:
                # 兼容性防御：如果底层的 writer.add_heading 还没有支持 align 参数，自动降级
                try:
                    writer.add_heading(part, level=heading_level, align=align)
                except TypeError as e:
                    if "align" in str(e):
                        writer.add_heading(part, level=heading_level)
                    else:
                        raise e
            else:
                writer.add_text(part, align=align)
