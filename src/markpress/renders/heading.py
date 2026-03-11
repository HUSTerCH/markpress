import re

from bs4 import BeautifulSoup
from reportlab.platypus import Paragraph, Spacer
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY

from .base import BaseRenderer
from ..utils.utils import strip_invalid_reportlab_img_tags


class HeadingRenderer(BaseRenderer):
    def render(self, text: str, level: int = 1, **kwargs):
        text = self._sanitize_heading_xml(text)
        if not text.strip():
            return []

        # 限制层级
        level = max(1, min(6, level))

        # 从 Config 获取样式数据 (例如 config.styles.headings.h1)
        h_style_conf = getattr(self.config.styles.headings, f"h{level}")

        # 动态生成/获取 ReportLab 样式
        style_name = f"Heading_{level}"
        if style_name not in self.styles:
            # 映射对齐字符串到 ReportLab 常量
            align_map = {'LEFT': TA_LEFT, 'CENTER': TA_CENTER, 'RIGHT': TA_RIGHT, 'JUSTIFY': TA_JUSTIFY}

            ps = ParagraphStyle(
                name=style_name,
                fontName=self.config.fonts.heading,
                fontSize=h_style_conf.font_size,
                leading=h_style_conf.leading,
                textColor=colors.HexColor(h_style_conf.color),
                alignment=align_map.get(h_style_conf.align, TA_LEFT),
                spaceBefore=h_style_conf.space_before,
                spaceAfter=h_style_conf.space_after,
                keepWithNext=False
            )
            self.styles.add(ps)

        # 返回组件
        return [Paragraph(text, self.styles[style_name])]

    def _sanitize_heading_xml(self, text: str) -> str:
        if not text:
            return ""

        text = re.sub(r'<a\s+name="\s*"\s*/?>', '', text)
        protected_imgs = {}

        def protect_match(match):
            key = f"__IMG_PROTECT_{len(protected_imgs)}__"
            protected_imgs[key] = match.group(0)
            return key

        text_safe = re.sub(r'<img\b[^>]*>', protect_match, text)
        soup = BeautifulSoup(text_safe, "html.parser")

        allowed_tags = {'b', 'i', 'u', 'strike', 'sup', 'sub', 'font', 'a', 'br', 'strong', 'em'}

        for tag in soup.find_all(True):
            if tag.name not in allowed_tags:
                tag.unwrap()
                continue

            if tag.name == "a":
                safe_attrs = {}
                href = (tag.get("href") or "").strip()
                name = (tag.get("name") or "").strip()
                if href:
                    safe_attrs["href"] = href
                if name:
                    safe_attrs["name"] = name

                if safe_attrs:
                    tag.attrs = safe_attrs
                else:
                    tag.unwrap()
            elif tag.name == "font":
                safe_attrs = {}
                for attr in ("color", "backColor", "backcolor", "face", "size"):
                    value = tag.get(attr)
                    if isinstance(value, str) and value.strip():
                        safe_attrs[attr] = value.strip()
                tag.attrs = safe_attrs
            else:
                tag.attrs = {}

        clean_html = str(soup)
        for key, original_img_tag in protected_imgs.items():
            tag_content = original_img_tag.strip()
            if not tag_content.endswith("/>"):
                tag_content = tag_content.rstrip(">") + "/>"
            clean_html = clean_html.replace(key, tag_content)

        clean_html = re.sub(r'<a[^>]*>\s*</a>', '', clean_html)
        clean_html = strip_invalid_reportlab_img_tags(clean_html)
        return clean_html
