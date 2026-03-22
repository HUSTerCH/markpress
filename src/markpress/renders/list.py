# 列表，包括有序和无序
import re
from typing import List, Union, Tuple

import emoji
from bs4 import BeautifulSoup
from reportlab.platypus import ListFlowable, ListItem
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle

from .base import BaseRenderer
from ..inherited.SafeCJKParagraph import SafeCJKParagraph
from ..inherited.SmartInlineImgParagraph import SmartInlineImgParagraph
from ..utils.utils import (
    MAX_INLINE_IMG_PT,
    replace_to_local_twemoji,
    scale_oversized_inline_imgs,
    strip_invalid_reportlab_img_tags,
)


class ListRenderer(BaseRenderer):
    def __init__(self, config, stylesheet):
        super().__init__(config, stylesheet)
        self._init_styles()

    def _init_styles(self):
        """初始化列表专用样式"""
        if "List_Body" not in self.styles:
            # 继承自正文样式
            body_style = self.styles["Body_Text"]
            self.styles.add(ParagraphStyle(
                name="List_Body",
                parent=body_style,
                # 列表项通常比正文稍微紧凑一点
                spaceAfter=2,
                # 行距一致
                leading=body_style.leading,
                fontName=body_style.fontName,
                fontSize=body_style.fontSize,
                textColor=body_style.textColor
            ))

    def render(self, items: List[Union[str, list]], is_ordered: bool = False, start_index: int = 1):
        """
        渲染入口
        :param start_index: 起始编号，只在有序列表中生效
        :param items: 嵌套列表数据 ['Item 1', ['Sub 1'], 'Item 2']
        :param is_ordered: 是否有序
        """
        if not items:
            return []

        # 构建 ListFlowable
        list_flowable = self._build_level(items, depth=0, ordered=is_ordered, start_index=start_index)
        if list_flowable is None:
            return []
        return [list_flowable]

    def _to_roman(self, n: int) -> str:
        """整数转罗马数字 (小写)"""
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

    def _get_symbol_and_font(self, depth: int, index: int, ordered: bool) -> Tuple[str, str]:
        """
        根据深度和类型决定符号与字体
        Returns: (symbol_char, font_name)
        """
        cycle = depth % 3

        # 优先使用配置字体，如果没有配置则回退到硬编码
        font_sc = self.config.fonts.regular  # 使用正文字体 (通常支持中文)
        font_mono = self.config.fonts.code  # 使用代码字体 (通常包含丰富的符号)

        if ordered:
            # 有序列表: 1. -> a. -> i.
            if cycle == 0:
                return f"{index}.", font_sc
            elif cycle == 1:
                # a. b. c.
                return f"{chr(96 + index)}.", font_sc
            else:
                # i. ii. iii.
                return f"{self._to_roman(index)}.", font_sc
        else:
            # 无序列表: • -> ◦ -> ▪
            if cycle == 0:
                return '•', font_sc  # 实心圆点
            elif cycle == 1:
                return '◦', font_mono  # 空心圆 (Mono字体通常对齐更好)
            else:
                return '▪', font_mono  # 实心方块

    def _build_level(self, sub_items: list, depth: int = 0, ordered: bool = False, start_index: int = 1) -> ListFlowable:
        """
        递归构建列表层级
        """
        if not sub_items:
            return None

        flowables = []
        item_index = start_index - 1
        i = 0

        # 获取当前主题的文本颜色
        text_color = colors.HexColor(self.config.colors.text_primary)

        while i < len(sub_items):
            item = sub_items[i]

            # 遇到列表直接跳过 (因为它是作为上一个 item 的子项处理的)
            # 除非数据结构异常（列表开头就是列表），这里做个简单兼容
            if isinstance(item, list):
                i += 1
                continue

            # 处理正常 Item
            item_index += 1

            # 获取符号
            bullet_char, bullet_font = self._get_symbol_and_font(depth, item_index, ordered)

            raw_text = self._sanitize_item_text(str(item))
            img_heights = [float(h) for h in re.findall(r'height="([\d\.]+)"', raw_text)]
            max_img_h = max(img_heights) if img_heights else 0
            max_img_h = min(max_img_h, MAX_INLINE_IMG_PT)
            # print("raw_text:", raw_text)
            # print("最大img高度：", max_img_h)

            base_style = self.styles["List_Body"]
            final_style = base_style

            # 给公式图上下留出 4pt 的呼吸空间
            required_leading = max_img_h + 2
            if required_leading > base_style.leading:
                extra_space_before = required_leading - base_style.leading
                final_style = ParagraphStyle(
                    name=f"List_Body_Dynamic_{id(raw_text)}",
                    parent=base_style,
                    leading=required_leading,
                    spaceBefore=base_style.spaceBefore + extra_space_before,
                )

            # 内容 (带图时改走更稳的 SmartInlineImgParagraph)
            paragraph_cls = SmartInlineImgParagraph if "<img" in raw_text else SafeCJKParagraph
            item_text = raw_text if raw_text.strip() else " "
            item_content = [paragraph_cls(item_text, final_style)]
            # print(item_content)

            # 预读下一项，如果是列表，则是当前项的子列表
            if i + 1 < len(sub_items) and isinstance(sub_items[i + 1], list):
                child_data = sub_items[i + 1]
                # 递归构建子 ListFlowable
                child_flowable = self._build_level(child_data, depth + 1, ordered)
                if child_flowable is not None:
                    item_content.append(child_flowable)
                i += 1  # 跳过已处理的子列表

            # 创建 ListItem
            # bulletOffsetY: 微调符号的垂直位置，防止跟文字对不齐
            flowables.append(ListItem(
                item_content,
                bulletColor=text_color,  # 适配深色模式
                value=bullet_char,
                bulletFontName=bullet_font,
                bulletFontSize=11,  # 稍微比正文小一点更精致
                bulletOffsetY=0.5
            ))

            i += 1

        # 构建 ListFlowable
        if not flowables:
            return None

        return ListFlowable(
            flowables,
            bulletType='bullet',  # 我们通过 ListItem 自定义了 bullet，这里设为 bullet 即可
            start=None,
            # 缩进控制
            leftIndent=18,  # 整体向右缩进
            bulletIndent=0,  # 符号相对于 leftIndent 的位置
            spaceBefore=2,
            spaceAfter=2
        )

    def _sanitize_item_text(self, text: str) -> str:
        if not text:
            return ""

        text = emoji.replace_emoji(text, replace=replace_to_local_twemoji)
        protected_imgs = {}

        def protect_match(match):
            key = f"__IMG_PROTECT_{len(protected_imgs)}__"
            protected_imgs[key] = match.group(0)
            return key

        text_safe = re.sub(r'<img\b[^>]*>', protect_match, text)
        soup = BeautifulSoup(text_safe, "html.parser")

        for tag in soup.find_all("span"):
            if not tag.has_attr("style"):
                tag.unwrap()
                continue

            styles = self._parse_css_style(tag["style"])
            new_tag = soup.new_tag("font")
            new_tag.extend(tag.contents)

            if "color" in styles:
                new_tag["color"] = styles["color"]
            if "background-color" in styles:
                new_tag["backColor"] = styles["background-color"]
            if "background" in styles:
                new_tag["backColor"] = styles["background"]

            tag.replace_with(new_tag)

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

        clean_html = re.sub(r'<font[^>]*>\s*</font>', '', clean_html)
        clean_html = re.sub(r'<(b|i|u|strong|em)[^>]*>\s*</\1>', '', clean_html)
        clean_html = re.sub(r'<a[^>]*>\s*</a>', '', clean_html)
        clean_html = re.sub(r'<a\s+name="\s*"\s*/?>', '', clean_html)
        clean_html = strip_invalid_reportlab_img_tags(clean_html)
        clean_html = scale_oversized_inline_imgs(clean_html)
        return clean_html

    @staticmethod
    def _parse_css_style(style_str: str) -> dict:
        styles = {}
        if not style_str:
            return styles

        for item in style_str.split(';'):
            if ':' in item:
                key, val = item.split(':', 1)
                styles[key.strip().lower()] = val.strip()
        return styles
