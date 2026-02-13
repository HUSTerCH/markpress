# MarkPress 核心功能测试
当前支持：
1. 代码块，已经修复代码块过大报错的问题
2. 正文富文本（持续测试中），暂不支持列表
## 1. 文本排版 (Typography)

这是标准正文文本。MarkPress 应该能够完美渲染**加粗文字 (Bold)**、*斜体文字 (Italic)*、***加粗和斜体(Bold and Italic)***。

> 这是单层嵌套这是单层嵌套这是单层嵌套这是单层嵌套这是单层嵌套这是单层嵌套这是单层嵌套这是单层嵌套这是单层嵌套这是单层嵌套这是单层嵌套这是单层嵌套这是单层嵌套这是单层嵌套这是单层嵌套

> 这是一段引用文本和这是一段引用文本和这是一段引用文本和这是一段引用文本和这是一段引用文本和这是一段引用文本和这是一段引用文本和
> > 嵌套引用文本嵌套引用文本嵌套引用文本嵌套引用文本嵌套引用文本嵌套引用文本嵌套引用文本嵌套引用文本
> > > 多级嵌套引用文本

同时也需要测试 中文长段落的自动换行 和 两端对齐 (Justify) 功能。如果这段文字足够长，它应该在PDF的右侧边界处整齐折行，而不是直接溢出页面或者留下难看的锯齿状边缘。工业级的排版要求中英文混排时（如 Python 与 C++）也能保持基线对齐。
这样的对齐方式才是看的赏心悦目的

再来试试font设置<font color="red">红色字体</font>和span设置<span style="background: yellow">黄色背景</span>

这是行内公式：$E=mc^2$

这是行间公式：

$$
x=\frac{-b±\sqrt{b^2-4ac}}{2a}
$$


<font size=20 color="green">行间html</font>


这是一个链接 *[Markdown语法](https://markdown.com.cn)*。

还可以这么写：<https://markdown.com.cn>

电子邮件：<fake@example.com>

分割线

---

### 1.1 字体测试 (Font Fallback)

Testing English font mixed with 中文显示. 1234567890 (Numbers).

## 2. 代码块 (Code Snippets)

下面是一段 Python 代码，用于测试`CodeRenderer`的背景色、边框以及`JetBrainsMono`字体渲染：

```python
import mistune
from .core import MarkPressEngine


def convert_markdown_file(input_path: str, output_path: str, theme: str = "academic"):
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
    writer.save()


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
            text = _render_inline(children)
            writer.add_heading(text, level=level)

        # --- 段落 (Paragraph) ---
        elif t_type == 'paragraph':
            text = _render_inline(children)
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
            print("识别到list，暂时跳过")
            # 列表需要递归处理，这里简化逻辑，把列表项转为 Python list 传给 writer
            # ordered = attrs.get('ordered', False)
            # list_items = _parse_list_items(children)
            # writer.add_list(list_items, is_ordered=attrs.get('ordered', False))

        # --- 表格 (Table) ---
        elif t_type == 'table':
            print("识别到table，暂时跳过")
            # table_data = _parse_table(children)
            # if table_data:
            #     writer.add_table(table_data)

        # --- 分隔线 (Thematic Break) ---
        elif t_type == 'thematic_break':
            writer.add_spacer(height_mm=2)
            # 可以画一条线，这里暂时用空行代替

        # --- 引用 (Blockquote) ---
        elif t_type == 'blockquote':
            # 引用里的内容其实也是 Block，递归调用
            # 暂时简单处理：遍历子元素，把文本加个前缀或颜色
            # 更好的做法是给 writer 加一个 add_blockquote 方法
            for child in children:
                if child['type'] == 'paragraph':
                    text = _render_inline(child['children'])
                    # 模拟引用样式：灰色斜体 (需要 writer 支持)
                    writer.add_text(text)


def _render_inline(tokens: list) -> str:
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
            # 必须转义 XML 字符，防止 & < > 破坏 PDF 结构
            text = tok.get('raw', '').replace('&', '&').replace('<', '<').replace('>', '>')
            result.append(text)

        elif t_type == 'strong':
            result.append(f"<b>{_render_inline(tok.get('children'))}</b>")

        elif t_type == 'emphasis':
            # ReportLab 的 Italic 需要字体支持，否则可能显示方框
            # 只要你注册了 Italic 字体就可以用 <i>
            result.append(f"<i>{_render_inline(tok.get('children'))}</i>")

        elif t_type == 'codespan':
            code = tok.get('raw', '').replace('&', '&').replace('<', '<').replace('>', '>')
            # 给行内代码加个背景色需要高级设置，这里简单加粗或换字体
            result.append(f'<font face="Courier" size="10">{code}</font>')

        elif t_type == 'link':
            text = _render_inline(tok.get('children'))
            href = tok.get('attrs', {}).get('url', '')
            # ReportLab 的超链接标签
            result.append(f'<a href="{href}" color="blue">{text}</a>')

        elif t_type == 'image':
            # 图片处理比较复杂，ReportLab 需要本地路径
            # 这里暂时只显示图片 Alt 文本，防止报错
            alt = tok.get('attrs', {}).get('alt', 'Image')
            result.append(f'[Image: {alt}]')

        elif t_type == 'softbreak':
            result.append(" ")  # 换行变空格

        elif t_type == 'linebreak':
            result.append("<br/>")  # 强制换行

    return "".join(result)


def _parse_list_items(list_children: list) -> list:
    """
    辅助函数：把 mistune 的 list tokens 解析成 writer.add_list 需要的嵌套列表结构
    """
    result = []
    for item in list_children:
        if item.get('type') == 'list_item':
            # list_item 的 children 通常是一个 paragraph 或者是 paragraph + nested list
            current_item_text = ""
            sub_list = None

            for child in item.get('children', []):
                if child.get('type') == 'paragraph':
                    current_item_text = _render_inline(child.get('children'))
                elif child.get('type') == 'list':
                    # 递归处理嵌套列表
                    sub_list = _parse_list_items(child.get('children'))

            result.append(current_item_text)
            if sub_list:
                result.append(sub_list)
    return result


def _parse_table(table_children: list) -> list:
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
                    cell_content = _render_inline(cell.get('children', []))
                    current_row.append(cell_content)
                rows.append(current_row)
    return rows
```

## 3. 样式层级 (Hierarchy)

### 三级标题 (H3)

正文内容...

正文内容...

正文内容...

正文内容...

正文内容...

### 三级标题
#### 四级标题 (H4)

这里测试紧凑的小标题样式。

```json
{
    "theme": "academic",
    "debug": true,
    "supported_formats": [
        "md",
        "rst"
    ]
}
```

