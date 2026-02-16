import re
from reportlab.platypus import Paragraph, Table, TableStyle, Spacer, KeepTogether
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm

# Pygments imports
try:
    from pygments import lex
    from pygments.lexers import get_lexer_by_name
    from pygments.token import Token

    HAS_PYGMENTS = True
except ImportError:
    HAS_PYGMENTS = False

from .base import BaseRenderer


class CodeRenderer(BaseRenderer):
    def __init__(self, config, stylesheet):
        super().__init__(config, stylesheet)
        self.token_color_map = self._build_token_map()

    def render(self, code: str, language: str = None, **kwargs):
        self._init_styles()

        code = code.strip()
        if not code: return []

        # 切片粒度
        MAX_LINES_PER_BLOCK = 2

        lines = code.split('\n')
        total_lines = len(lines)
        flowables = []

        original_language = language

        for i in range(0, total_lines, MAX_LINES_PER_BLOCK):
            chunk_lines = lines[i: i + MAX_LINES_PER_BLOCK]
            chunk_code = "\n".join(chunk_lines)

            is_first = (i == 0)
            is_last = (i + MAX_LINES_PER_BLOCK >= total_lines)

            t = self._create_table_card(
                chunk_code,
                original_language,
                kwargs.get('avail_width', 160 * mm),
                is_first,
                is_last
            )

            if is_first:
                # 只有第一块（含标题）不允许内部断开，防止孤儿标题
                flowables.append(KeepTogether([t]))
            else:
                flowables.append(t)
        return flowables + [Spacer(1, 10)]

    def _create_table_card(self, code_text, language, avail_width, is_first, is_last):
        xml_content = self._highlight_code_to_xml(code_text, language)
        code_para = Paragraph(xml_content, self.styles["Code_Block"])

        data = []

        # 只有第一块有标题行
        if is_first:
            lang_label = language.upper() if language else "CODE"
            title_para = Paragraph(lang_label, self.styles["Code_Title"])
            data.append([title_para])  # Row 0
            data.append([code_para])  # Row 1
        else:
            data.append([code_para])  # Row 0

        t = Table(data, colWidths=[avail_width])

        # 获取配置颜色
        code_conf = self.config.styles.code
        bg_color = colors.HexColor(code_conf.background_color)
        border_color = colors.HexColor(code_conf.border_color)

        # 动态边框逻辑，不使用 BOX (四边全围)，而是分别控制上下左右

        style_cmds = [
            ('BACKGROUND', (0, 0), (-1, -1), bg_color),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),

            # 左右边框：永远存在
            ('LINEBEFORE', (0, 0), (-1, -1), 0.5, border_color),
            ('LINEAFTER', (0, 0), (-1, -1), 0.5, border_color),
        ]

        # 上边框：只有第一块才有 (封顶)
        if is_first:
            style_cmds.append(('LINEABOVE', (0, 0), (-1, 0), 0.5, border_color))

        # 下边框：只有最后一块才有 (封底)
        if is_last:
            style_cmds.append(('LINEBELOW', (0, -1), (-1, -1), 0.5, border_color))

        # Padding 逻辑
        if is_first:
            style_cmds.extend([
                # 标题栏
                ('LEFTPADDING', (0, 0), (-1, 0), 10),
                ('TOPPADDING', (0, 0), (-1, 0), 6),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#555555")),

                # 代码栏
                ('LEFTPADDING', (0, 1), (-1, 1), 10),
                ('RIGHTPADDING', (0, 1), (-1, 1), 2),
                ('TOPPADDING', (0, 1), (-1, 1), 0),
                ('BOTTOMPADDING', (0, 1), (-1, 1), 8 if is_last else 0),  # 如果后面还有块，底部不要 padding
            ])
        else:
            style_cmds.extend([
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('RIGHTPADDING', (0, 0), (-1, -1), 2),
                ('TOPPADDING', (0, 0), (-1, -1), 0),  # 紧贴上一块
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8 if is_last else 0),  # 中间块不需要底部 padding
            ])

        t.setStyle(TableStyle(style_cmds))
        return t

    def _init_styles(self):
        if "Code_Block" in self.styles: return
        conf = self.config.styles.code

        self.styles.add(ParagraphStyle(
            name="Code_Block",
            fontName=self.config.fonts.code,
            fontSize=conf.font_size,
            leading=conf.font_size * 1.5,
            textColor=colors.HexColor(self.config.colors.text_primary),
            wordWrap='CJK',
            splitLongWords=True,
        ))

        self.styles.add(ParagraphStyle(
            name="Code_Title",
            fontName=self.config.fonts.heading,
            fontSize=max(6, conf.font_size - 1.5),
            leading=conf.font_size,
            textColor=colors.HexColor("#555555"),
            spaceAfter=0
        ))

    def _build_token_map(self):
        if not HAS_PYGMENTS: return {}
        json_map = self.config.styles.code.highlight_colors
        token_map = {}
        for key_str, hex_color in json_map.items():
            try:
                parts = key_str.split('.')
                current_token = Token
                for part in parts:
                    current_token = getattr(current_token, part)
                token_map[current_token] = hex_color
            except AttributeError:
                continue
        return token_map

    def _highlight_code_to_xml(self, code, language):
        def escape_html(s):
            return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;') \
                .replace(' ', '&nbsp;').replace('\n', '<br/>')

        def wrap_cjk(text):
            return re.sub(r'([\u4e00-\u9fa5\u3000-\u303f\uff00-\uffef]+)',
                          r'<font face="HarmonySC">\1</font>', text)

        if not HAS_PYGMENTS or not language:
            return wrap_cjk(escape_html(code))

        try:
            lexer = get_lexer_by_name(language)
        except:
            return wrap_cjk(escape_html(code))

        tokens = lex(code, lexer)
        out_xml = ""

        for token_type, value in tokens:
            value = escape_html(value)
            value = wrap_cjk(value)
            color = None
            curr = token_type
            while curr is not None:
                if curr in self.token_color_map:
                    color = self.token_color_map[curr]
                    break
                curr = curr.parent
            if color:
                out_xml += f'<font color="{color}">{value}</font>'
            else:
                out_xml += value
        return out_xml