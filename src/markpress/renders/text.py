import copy
import re
import emoji
from bs4 import BeautifulSoup  # [NEW]
from bs4 import NavigableString
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph

from .base import BaseRenderer
from ..inherited.SmartInlineImgParagraph import SmartInlineImgParagraph
from ..utils import replace_to_twemoji, replace_to_local_twemoji


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
                splitLongWords=True,
                keepWithNext=False
            ))

    def render(self, xml_text: str, align: str = 'left', **kwargs):
        # 清洗并修复 HTML 结构
        clean_text = self._sanitize_html_for_reportlab(xml_text).replace("\n", "")
        img_heights = [float(h) for h in re.findall(r'height="([\d\.]+)"', clean_text)]
        max_img_h = max(img_heights) if img_heights else 0

        # 获取基础样式
        base_style = self.styles["Body_Text"]
        final_style = base_style
        required_leading = max_img_h + 4

        if required_leading > base_style.leading:
            # 必须 copy 一份样式，否则会修改全局单例，导致后面的普通段落也变得很宽
            final_style = copy.copy(base_style)
            final_style.leading = required_leading
            # 如果公式太高，让它稍微居中一点，可以增加 spaceBefore/After
            # final_style.spaceAfter += 2
        if align == 'center':
            final_style.alignment = TA_CENTER
        elif align == 'right':
            final_style.alignment = TA_RIGHT
        else:
            final_style.alignment = TA_LEFT

        if "<img" in clean_text :
            # print("这是有img的clean text：", clean_text)
            # print("其style的alignment为：", final_style.alignment)
            # if align == "center":
            #     clean_text = f"&nbsp;{clean_text}&nbsp;"
            # elif align == "right":
            #     clean_text = f"&nbsp;{clean_text}"
            return [SmartInlineImgParagraph(clean_text, final_style)]
        else:
            return [Paragraph(clean_text, self.styles["Body_Text"])]

    def _sanitize_html_for_reportlab(self, text: str) -> str:
        """
        工程化清洗：
        1. 保护 <img ... />
        2. BS4 结构修复
        3. 还原 img
        4. 清除空标签
        """
        if not text:
            return ""

        # text = emoji.replace_emoji(text, replace=replace_to_twemoji)
        text = emoji.replace_emoji(text, replace=replace_to_local_twemoji)

        # --- [Step 1] 保护 <img /> 标签 ---
        protected_imgs = {}

        def protect_match(match):
            key = f"__IMG_PROTECT_{len(protected_imgs)}__"
            protected_imgs[key] = match.group(0)
            return key

        text_safe = re.sub(r'<img[^>]+>', protect_match, text)

        # --- [Step 2] BS4 清洗 ---
        soup = BeautifulSoup(text_safe, "html.parser")

        # 转换 span -> font
        for tag in soup.find_all("span"):
            if not tag.has_attr("style"):
                tag.unwrap()
                continue

            style_str = tag["style"]
            styles = self._parse_css_style(style_str)

            new_tag = soup.new_tag("font")
            new_tag.extend(tag.contents)

            if "color" in styles:
                new_tag["color"] = styles["color"]
            if "background-color" in styles:
                new_tag["backColor"] = styles["background-color"]
            if "background" in styles:
                new_tag["backColor"] = styles["background"]

            tag.replace_with(new_tag)

        # 白名单过滤
        ALLOWED_TAGS = {'b', 'i', 'u', 'strike', 'sup', 'sub', 'font', 'a', 'br', 'strong', 'em'}
        for tag in soup.find_all(True):
            if tag.name not in ALLOWED_TAGS:
                tag.unwrap()

        clean_html = str(soup)

        # --- [Step 3] 还原 <img /> (带空格) ---
        for key, original_img_tag in protected_imgs.items():
            # 确保原始标签一定是自闭合的，并且斜杠前有空格
            tag_content = original_img_tag.strip()

            # 如果是 <img ...> (没闭合) -> <img ... />
            if not tag_content.endswith("/>"):
                tag_content = tag_content.rstrip(">") + "/>"
            elif tag_content.endswith("/>") and not tag_content.endswith("/>"):
                tag_content = tag_content[:-2] + "/>"

            clean_html = clean_html.replace(key, tag_content)

        # --- [Step 4] 最后的防线：清理空标签 ---
        # 空的 font/b/i 标签会导致 CJK Crash，必须清理
        # 使用正则循环清理，直到没有空标签为止 (处理嵌套空标签 <b><i></i></b>)
        # 清理空 font
        clean_html = re.sub(r'<font[^>]*>\s*</font>', '', clean_html)
        # 清理空 b/i/u/strong/em
        clean_html = re.sub(r'<(b|i|u|strong|em)[^>]*>\s*</\1>', '', clean_html)
        # print("清洗前：", text)
        # print("清洗后：", clean_html)
        return clean_html

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
