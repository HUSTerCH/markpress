# from reportlab.platypus import Paragraph
# from reportlab.lib.styles import ParagraphStyle
# from reportlab.lib import colors
# from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
# from .base import BaseRenderer
#
#
# class TextRenderer(BaseRenderer):
#     def __init__(self, config, stylesheet):
#         super().__init__(config, stylesheet)
#         self._init_body_style()
#
#     def _init_body_style(self):
#         """初始化基础正文样式"""
#         if "Body_Text" not in self.styles:
#             conf = self.config.styles.body
#             align_map = {'LEFT': TA_LEFT, 'CENTER': TA_CENTER, 'RIGHT': TA_RIGHT, 'JUSTIFY': TA_JUSTIFY}
#
#             self.styles.add(ParagraphStyle(
#                 name="Body_Text",
#                 fontName=self.config.fonts.regular,
#                 fontSize=conf.font_size,
#                 leading=conf.leading,
#                 alignment=align_map.get(conf.alignment, TA_JUSTIFY),
#                 spaceAfter=conf.space_after,
#                 textColor=colors.HexColor(self.config.colors.text_primary),
#                 wordWrap='CJK'  # 必须开启，否则中文不换行
#             ))
#
#     def render(self, xml_text: str, **kwargs):
#         """
#         :param xml_text: 已经转义并包含 XML 标签的文本 (如 <b>Text</b>)
#         """
#         # 注意：这里的 xml_text 必须已经在外部 (Converter层) 处理过转义
#         print(xml_text)
#         return [Paragraph(xml_text, self.styles["Body_Text"])]

import re
from bs4 import BeautifulSoup, NavigableString  # [NEW]
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from .base import BaseRenderer


class TextRenderer(BaseRenderer):
    def __init__(self, config, stylesheet):
        super().__init__(config, stylesheet)
        self._init_body_style()

    def _init_body_style(self):
        # ... (保持原样) ...
        if "Body_Text" not in self.styles:
            conf = self.config.styles.body
            align_map = {'LEFT': TA_LEFT, 'CENTER': TA_CENTER, 'RIGHT': TA_RIGHT, 'JUSTIFY': TA_JUSTIFY}

            self.styles.add(ParagraphStyle(
                name="Body_Text",
                fontName=self.config.fonts.regular,
                fontSize=conf.font_size,
                leading=conf.leading,
                alignment=align_map.get(conf.alignment, TA_JUSTIFY),
                spaceAfter=conf.space_after,
                textColor=colors.HexColor(self.config.colors.text_primary),
                wordWrap='CJK',
                splitLongWords=True
            ))

    def render(self, xml_text: str, **kwargs):
        # 清洗并修复 HTML 结构
        clean_text = self._sanitize_html_for_reportlab(xml_text).replace("\n","")
        return [Paragraph(clean_text, self.styles["Body_Text"])]

    def _sanitize_html_for_reportlab(self, text: str) -> str:
        """
        使用 BeautifulSoup 修复畸形 HTML，并将 CSS 样式转换为 ReportLab XML 属性。
        解决:
        1. 结构错误 (如 </font></font>)
        2. 样式转换 (span style -> font color/backColor)
        """
        if not text:
            return ""

        # 1. 使用 html.parser 宽松解析 (自动修复闭合标签错误)
        # 即使输入是 "a</font></font>b", BS4 也会把它修成 "a</font>b" (忽略多余的)
        soup = BeautifulSoup(text, "html.parser")

        # 2. 遍历并转换标签 (ReportLab 不支持 span style，只支持 font)
        # find_all 会递归查找
        for tag in soup.find_all("span"):
            if not tag.has_attr("style"):
                print("span 没有style")
                # 无样式的 span，直接拆包 (Unwrap)，只保留内容
                tag.unwrap()
                continue

            # 解析 style 字符串
            style_str = tag["style"]
            styles = self._parse_css_style(style_str)

            # 转换为 ReportLab 的 font 标签
            # 创建新 tag
            new_tag = soup.new_tag("font")

            # 迁移内容
            new_tag.extend(tag.contents)

            # 映射属性
            if "color" in styles:
                new_tag["color"] = styles["color"]
            if "background-color" in styles:
                new_tag["backColor"] = styles["background-color"]
            if "background" in styles:
                new_tag["backColor"] = styles["background"]
            # 还可以支持 face (font-family) 等

            # 替换旧 tag
            tag.replace_with(new_tag)

        # 3. 处理 ReportLab 不支持的其他标签 (如 div, p 等)
        # 如果 Markdown 解析器生成了 div，我们需要把它拆掉，只留文字
        # 允许的白名单: b, i, u, strike, super, sub, font, a, br, img
        ALLOWED_TAGS = {'b', 'i', 'u', 'strike', 'sup', 'sub', 'font', 'a', 'br', 'img', 'strong', 'em'}

        for tag in soup.find_all(True):
            if tag.name not in ALLOWED_TAGS:
                # 遇到不支持的标签 (如 div, span剩下的)，直接拆包，保留内部文字和子标签
                # 这样可以防止 ReportLab 报错
                tag.unwrap()

        # 4. 输出修正后的 XML
        # decode_contents() 返回标签内的 XML 字符串，不包含最外层的 document 结构
        return str(soup)

    def _parse_css_style(self, style_str: str) -> dict:

        """简单的 CSS 解析器: 'color: red; background-color: yellow' -> dict"""
        styles = {}
        if not style_str:
            return styles

        for item in style_str.split(';'):
            if ':' in item:
                key, val = item.split(':', 1)
                styles[key.strip().lower()] = val.strip()
        return styles