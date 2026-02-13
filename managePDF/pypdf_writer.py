import io
import re
from pathlib import Path
from typing import List, Union, Optional

import matplotlib.pyplot as plt
# ReportLab imports
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    ListFlowable, ListItem, PageBreak, Image as PlatypusImage
)

# External libs
try:
    # Pygments 用于解析代码 token，不再用于生成图片
    from pygments import lex
    from pygments.lexers import get_lexer_by_name
    from pygments.token import Token

    HAS_EXT_LIBS = True
except ImportError:
    HAS_EXT_LIBS = False
    print("Warning: pygments not found. Code highlighting will be disabled.")


class PyPDFWriter:
    def __init__(self, filename: str, title: str = "Generated Report", author: str = "PyPDFWriter"):
        self.filename = filename
        self.base_dir = Path(__file__).parent
        self.story = []

        # 1. 注册字体
        self._register_fonts()

        # 2. 初始化样式
        self.styles = getSampleStyleSheet()
        self._init_custom_styles()

        # 3. 文档模板
        self.doc = SimpleDocTemplate(
            self.filename,
            pagesize=A4,
            rightMargin=25 * mm,
            leftMargin=25 * mm,
            topMargin=25 * mm,
            bottomMargin=25 * mm,
            title=title,
            author=author
        )

    def _register_fonts(self):
        """注册字体"""
        harmony_dir = self.base_dir / "HarmonyOS_Sans"
        jetbrains_dir = self.base_dir / "JetBrains_Mono"

        # --- HarmonyOS Sans ---
        reg_path = harmony_dir / "HarmonySC-Regular.ttf"
        reg_italic_path = harmony_dir / "HarmonySC-Italic.ttf"
        bold_path = harmony_dir / "HarmonySC-Bold.ttf"
        bold_italic_path = harmony_dir / "HarmonySC-Bold-Italic.ttf"

        if not reg_path.exists():
            raise FileNotFoundError(f"Font missing: {reg_path}")

        pdfmetrics.registerFont(TTFont("HarmonySC", reg_path))
        pdfmetrics.registerFont(TTFont("HarmonySC-Italic", reg_italic_path))
        pdfmetrics.registerFont(TTFont("HarmonySC-Bold", bold_path))
        pdfmetrics.registerFont(TTFont("HarmonySC-Bold-Italic", bold_italic_path))

        pdfmetrics.registerFontFamily(
            "HarmonySC",
            normal="HarmonySC",
            bold="HarmonySC-Bold",
            italic="HarmonySC-Italic",
            boldItalic="HarmonySC-Bold-Italic",
        )

        # --- JetBrains Mono (用于代码) ---
        jb_reg = jetbrains_dir / "JetBrainsMono-Regular.ttf"
        if jb_reg.exists():
            pdfmetrics.registerFont(TTFont("JetBrainsMono", jb_reg))
            self.has_code_font = True
        else:
            self.has_code_font = False

    def _init_custom_styles(self):
        base_font = "HarmonySC"
        bold_font = "HarmonySC-Bold"

        # 正文
        self.styles.add(ParagraphStyle(
            name="Body_CN",
            fontName=base_font,
            fontSize=11,
            leading=18,
            spaceAfter=8,
            alignment=TA_JUSTIFY,
            wordWrap='CJK'
        ))

        # 列表内容样式
        self.styles.add(ParagraphStyle(
            name="ListBody",
            parent=self.styles["Body_CN"],
            spaceAfter=0,  # 列表项紧凑
            leading=16,
        ))

        # 代码段落样式 (用于放在 Table 里)
        self.styles.add(ParagraphStyle(
            name="CodePara",
            fontName="JetBrainsMono" if self.has_code_font else "Courier",
            fontSize=9,
            leading=12,
            leftIndent=0,
            wordWrap='CJK',
        ))

        # 标题 (H1-H5)
        configs = [
            ("H1_CN", 22, 28, 16, 16, bold_font),
            ("H2_CN", 18, 24, 12, 10, bold_font),
            ("H3_CN", 15, 20, 10, 8, bold_font),
            ("H4_CN", 13, 18, 6, 6, bold_font),
            ("H5_CN", 11, 16, 6, 6, bold_font),
        ]
        for name, size, lead, sb, sa, font in configs:
            self.styles.add(ParagraphStyle(
                name=name, fontName=font, fontSize=size, leading=lead,
                spaceBefore=sb, spaceAfter=sa, keepWithNext=True
            ))

    # ================= 核心功能 =================

    # def add_heading(self, text: str, level: int = 1, align: str = 'LEFT'):
    #     level = max(1, min(5, level))
    #     style = self.styles[f"H{level}_CN"]
    #     align_map = {'LEFT': TA_LEFT, 'CENTER': TA_CENTER, 'RIGHT': TA_RIGHT}
    #     style.alignment = align_map.get(align.upper(), TA_LEFT)
    #     self.story.append(Paragraph(text, style))

    def add_heading(self, text: str, level: int = 1, align: str = 'LEFT'):
        level = max(1, min(5, level))
        base_style_name = f"H{level}_CN"

        align_map = {'LEFT': TA_LEFT, 'CENTER': TA_CENTER, 'RIGHT': TA_RIGHT}
        target_align = align_map.get(align.upper(), TA_LEFT)
        # 不直接修改 self.styles[...]，而是以它为 parent 创建一个新的临时样式
        # 这样每个标题的对齐方式就是独立的，互不干扰
        heading_style = ParagraphStyle(
            name=f"Heading_{level}_{align}",  # 给个临时名字
            parent=self.styles[base_style_name],
            alignment=target_align
        )

        self.story.append(Paragraph(text, heading_style))

    def add_text(self, text: str, style="Body_CN", **kwargs):
        p_style = ParagraphStyle('temp', parent=self.styles[style])
        if 'align' in kwargs:
            align_map = {'LEFT': TA_LEFT, 'CENTER': TA_CENTER, 'RIGHT': TA_RIGHT, 'JUSTIFY': TA_JUSTIFY}
            p_style.alignment = align_map.get(kwargs['align'].upper(), TA_LEFT)
        if 'color' in kwargs:
            p_style.textColor = getattr(colors, kwargs['color'], colors.black)
        self.story.append(Paragraph(text.replace("\n", "<br/>"), p_style))

    def add_spacer(self, height_mm=5):
        self.story.append(Spacer(1, height_mm * mm))

    def add_page_break(self):
        self.story.append(PageBreak())

    def add_list(self, items: List[Union[str, list]], is_ordered=False):
        def to_roman(n):
            val = [10, 9, 5, 4, 1]
            syb = ["x", "ix", "v", "iv", "i"]
            roman_num = ''
            i = 0
            while n > 0:
                for _ in range(n // val[i]):
                    roman_num += syb[i]
                    n -= val[i]
                i += 1
            return roman_num

        def get_symbol_and_font(depth, index, ordered):
            """
            返回 (符号字符串, 字体名称)
            """
            cycle = depth % 3

            if ordered:
                # 有序列表
                font = "HarmonySC"
                if cycle == 0:
                    return (f"{index}.", font)
                elif cycle == 1:
                    return (f"{chr(96 + index)}.", font)  # a. b.
                else:
                    return (f"{to_roman(index)}.", font)  # i. ii.
            else:
                # 无序列表
                if cycle == 0:
                    # 实心圆点
                    return ('•', "HarmonySC")
                elif cycle == 1:
                    # 空心圆
                    return ('◦', "JetBrainsMono")
                else:
                    # 实心方块
                    return ('▪', "JetBrainsMono")

        def build_level(sub_items, depth=0, ordered=False):
            flowables = []
            item_index = 0
            i = 0
            while i < len(sub_items):
                item = sub_items[i]

                if isinstance(item, list):
                    pass
                else:
                    item_index += 1
                    # 1. 获取符号和该符号应使用的字体
                    bullet_char, bullet_font = get_symbol_and_font(depth, item_index, ordered)

                    # 2. 内容
                    item_content = [Paragraph(str(item), self.styles["ListBody"])]

                    # 3. 递归子项
                    if i + 1 < len(sub_items) and isinstance(sub_items[i + 1], list):
                        child_data = sub_items[i + 1]
                        child_flowable = build_level(child_data, depth + 1, ordered)
                        item_content.append(child_flowable)
                        i += 1

                    # 4. 创建 ListItem (关键：针对每个Item单独设置 bulletFontName)
                    flowables.append(ListItem(
                        item_content,
                        bulletColor=colors.black,
                        value=bullet_char,
                        bulletFontName=bullet_font,
                        bulletFontSize=11
                    ))
                i += 1

            return ListFlowable(
                flowables,
                bulletType='bullet',
                start=None,
                # 缩进控制
                leftIndent=20,  # 文本距离左边的距离 (越小越紧凑)
                bulletIndent=0,  # 符号距离左边的距离
            )

        self.story.append(build_level(items, 0, is_ordered))
        self.add_spacer(2)

    # 定义预置的代码高亮主题
    def _highlight_code_to_xml(self, code, language, theme="vscode"):
        """
        代码高亮转 XML (修复版 + 多主题支持)
        :param theme: 可选 "vscode", "github", "monokai", "intellij"
        """
        # --- 1. 预定义颜色主题 (Tokens to Hex Colors) ---
        themes = {
            "vscode": {  # VS Code Dark (Default-like)
                Token.Keyword: "#C586C0", Token.Name.Function: "#DCDCAA",
                Token.Name.Class: "#4EC9B0", Token.String: "#CE9178",
                Token.Comment: "#6A9955", Token.Number: "#B5CEA8",
                Token.Operator: "#D4D4D4", Token.Text: "#333333"
            },
            "github": {  # GitHub Light
                Token.Keyword: "#d73a49", Token.Name.Function: "#6f42c1",
                Token.Name.Class: "#6f42c1", Token.String: "#032f62",
                Token.Comment: "#6a737d", Token.Number: "#005cc5",
                Token.Operator: "#d73a49", Token.Text: "#24292e"
            },
            "intellij": {  # IntelliJ IDEA Light
                Token.Keyword: "#0033b3", Token.Name.Function: "#00627a",
                Token.Name.Class: "#000000", Token.String: "#067d17",
                Token.Comment: "#8c8c8c", Token.Number: "#1750eb",
                Token.Operator: "#000000", Token.Text: "#080808"
            },
            "monokai": {  # Monokai (Adapted for light bg)
                Token.Keyword: "#F92672", Token.Name.Function: "#A6E22E",
                Token.Name.Class: "#A6E22E", Token.String: "#E6DB74",
                Token.Comment: "#75715E", Token.Number: "#AE81FF",
                Token.Operator: "#F92672", Token.Text: "#272822"
            }
        }

        # 获取当前主题映射，默认为 vscode
        colors_map = themes.get(theme, themes["vscode"])

        # --- 2. 内部函数：中文修复 ---
        def wrap_cjk(text):
            return re.sub(r'([\u4e00-\u9fa5\u3000-\u303f\uff00-\uffef]+)',
                          r'<font face="HarmonySC">\1</font>', text)

        if not HAS_EXT_LIBS:
            safe_code = code.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            safe_code = safe_code.replace(' ', '&nbsp;').replace('\n', '<br/>')
            return wrap_cjk(safe_code)

        try:
            lexer = get_lexer_by_name(language)
            tokens = lex(code, lexer)
            out_xml = ""

            for token_type, value in tokens:
                # A. 转义
                value = value.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

                # B. 格式化 (先处理空格换行)
                value = value.replace(' ', '&nbsp;').replace('\n', '<br/>')

                # C. 修复中文
                value = wrap_cjk(value)

                # D. 上色
                # 尝试获取精确类型，如果没有则尝试父类型
                color = colors_map.get(token_type) or colors_map.get(token_type.parent)

                if color:
                    out_xml += f'<font color="{color}">{value}</font>'
                else:
                    # 如果没有高亮颜色，也可以设置一个默认颜色(可选)
                    out_xml += value

            return out_xml
        except Exception as e:
            print(f"Highlight error: {e}")
            safe_code = code.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            safe_code = safe_code.replace(' ', '&nbsp;').replace('\n', '<br/>')
            return wrap_cjk(safe_code)

    def add_code(self, code_str: str, language: str = "python", theme: str = "github"):
        """
        添加代码块：带左上角 HarmonyOS 小标题 + 代码正文
        """
        # --- 1. 准备内容 ---
        # 转换代码内容
        xml_content = self._highlight_code_to_xml(code_str, language, theme=theme)
        code_para = Paragraph(xml_content, self.styles["CodePara"])

        # 创建左上角的小标题 (Language Title)
        # 使用 HarmonySC-Bold，字号设为 7.5 (比代码的9略小)，颜色深灰
        title_style = ParagraphStyle(
            name="CodeTitle",
            fontName="HarmonySC-Bold",
            fontSize=7.5,
            leading=10,
            textColor=colors.HexColor("#555555"),  # 深灰色，不抢眼
            spaceAfter=0
        )
        # 显示语言名称，转大写 (如 PYTHON, JSON)
        title_text = language.upper() if language else "CODE"
        title_para = Paragraph(title_text, title_style)

        # --- 2. 创建表格 (两行一列) ---
        # 第一行：Title
        # 第二行：Code
        # 宽度：160mm (A4内容宽)
        data = [
            [title_para],
            [code_para]
        ]

        t = Table(data, colWidths=[160 * mm])

        # --- 3. 样式设置 (模拟一体化卡片) ---
        t.setStyle(TableStyle([
            # === 全局设置 ===
            ('BACKGROUND', (0, 0), (-1, -1), colors.whitesmoke),  # 整体灰色背景
            ('BOX', (0, 0), (-1, -1), 0.5, colors.lightgrey),  # 整体外边框
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),

            # === 第一行 (Title) 样式 ===
            # 左上角，padding稍微小一点，紧凑
            ('LEFTPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 6),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 0),  # 标题和代码之间不要有太多空隙

            # === 第二行 (Code) 样式 ===
            # 代码部分
            ('LEFTPADDING', (0, 1), (-1, 1), 10),
            ('RIGHTPADDING', (0, 1), (-1, 1), 10),
            ('TOPPADDING', (0, 1), (-1, 1), 2),  # 代码离标题近一点
            ('BOTTOMPADDING', (0, 1), (-1, 1), 8),  # 底部留白
        ]))

        self.story.append(t)
        self.add_spacer(4)

    def add_table(self, data: List[List[str]], col_widths: Optional[List[float]] = None, has_header: bool = True):
        if not data: return

        def get_visual_weight(html_text):
            if not isinstance(html_text, str):
                return len(str(html_text))

            # 正则去除所有 XML/HTML 标签 (<...>)
            # 匹配 < 开头，中间非 > 的字符，直到 > 结尾
            clean_text = re.sub(r'<[^>]+>', '', html_text)

            # 处理常见的 XML 转义字符
            clean_text = clean_text.replace('&nbsp;', ' ') \
                .replace('&lt;', '<') \
                .replace('&gt;', '>') \
                .replace('&amp;', '&') \
                .replace('&quot;', '"')

            # 计算视觉宽度 (汉字=2, ASCII=1)
            weight = 0
            for char in clean_text:
                if ord(char) > 255:
                    weight += 2
                else:
                    weight += 1
            return weight

        available_width = 160 * mm

        if col_widths is None:
            col_count = len(data[0])
            if col_count > 0:
                col_weights_total = [0] * col_count
                row_count = len(data)

                for row in data:
                    for i, cell in enumerate(row):
                        weight = get_visual_weight(str(cell))
                        # 基础缓冲 +2，防止极短内容导致列宽太窄
                        col_weights_total[i] += (weight + 2)

                # 计算平均权重
                avg_weights = [total / row_count for total in col_weights_total]
                total_weight = sum(avg_weights)

                if total_weight == 0:
                    col_widths = [available_width / col_count] * col_count
                else:
                    # 按比例分配 A4 宽度
                    col_widths = [(w / total_weight) * available_width for w in avg_weights]

        center_style = ParagraphStyle(
            name="CellCenter",
            parent=self.styles["Body_CN"],
            alignment=TA_CENTER,
            wordWrap='CJK'  # 确保中文在单元格内正确换行
        )

        processed_data = []
        for row_idx, row in enumerate(data):
            new_row = []
            for cell in row:
                content = cell
                if isinstance(cell, str):
                    if has_header and row_idx == 0:
                        content = f"<b>{cell}</b>"
                    new_row.append(Paragraph(str(content).replace("\n", "<br/>"), center_style))
                else:
                    new_row.append(cell)
            processed_data.append(new_row)

        # 创建表格
        tbl = Table(processed_data, colWidths=col_widths, hAlign="CENTER")

        # 样式定义
        table_style_cmds = [
            ('FONTNAME', (0, 0), (-1, -1), "HarmonySC"),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('LEADING', (0, 0), (-1, -1), 14),

            # 垂直居中 (MIDDLE) + 水平居中 (CENTER)
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),

            # 边距
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),

            # Excel 网格线
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]

        if has_header:
            table_style_cmds.append(('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f0f0f0")))

        tbl.setStyle(TableStyle(table_style_cmds))

        self.story.append(tbl)
        self.add_spacer(4)

    def add_formula(self, latex_str: str, fontsize=12):
        """
        插入 LaTeX 公式。
        原理：使用 Matplotlib 渲染 LaTeX 为图片，然后插入 PDF。
        """
        if not HAS_EXT_LIBS:
            self.add_text(f"[Formula: {latex_str}] (Matplotlib not installed)", color='red')
            return

        try:
            # 1. 配置 Matplotlib 渲染
            fig = plt.figure(figsize=(0.1, 0.1))  # 这里的尺寸不重要，bbox_inches='tight' 会裁剪
            # 使用 sans-serif 看起来更现代，或者 'stix' 像 latex
            plt.rc('mathtext', fontset='stix')

            # 渲染文字（不可见，仅用于生成）
            # $$ 包裹以启用数学模式
            text = f"${latex_str}$"
            fig.text(0, 0, text, fontsize=fontsize)

            # 2. 保存到内存 Buffer
            buf = io.BytesIO()
            plt.axis('off')  # 关闭坐标轴
            # bbox_inches='tight', pad_inches=0.05 确保只裁剪公式部分
            plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0.05, dpi=300, transparent=True)
            plt.close(fig)

            buf.seek(0)

            # 3. 插入 PDF
            img = PlatypusImage(buf)
            # 调整一下显示比例 (Matplotlib 300dpi 出来的图比较大)
            # 简单算法：按比例缩小以匹配文字大小，这里简单除以 3
            img.drawHeight = img.drawHeight / 3
            img.drawWidth = img.drawWidth / 3

            self.story.append(img)
            self.add_spacer(2)

        except Exception as e:
            self.add_text(f"[Formula Error: {str(e)}]", color='red')

    def save(self):
        try:
            self.doc.build(self.story)
            print(f"✅ PDF Success: {self.filename}")
        except Exception as e:
            print(f"❌ PDF Failed: {e}")
