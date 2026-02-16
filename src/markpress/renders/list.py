# 列表，包括有序和无序
from typing import List, Union, Tuple
from reportlab.platypus import ListFlowable, ListItem
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle

from .base import BaseRenderer
from ..inherited.SafeCJKParagraph import SafeCJKParagraph


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

    def render(self, items: List[Union[str, list]], is_ordered: bool = False):
        """
        渲染入口
        :param items: 嵌套列表数据 ['Item 1', ['Sub 1'], 'Item 2']
        :param is_ordered: 是否有序
        """
        # 构建 ListFlowable
        list_flowable = self._build_level(items, depth=0, ordered=is_ordered)
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

    def _build_level(self, sub_items: list, depth: int = 0, ordered: bool = False) -> ListFlowable:
        """
        递归构建列表层级
        """
        flowables = []
        item_index = 0
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

            # 1获取符号
            bullet_char, bullet_font = self._get_symbol_and_font(depth, item_index, ordered)

            # 内容 (使用 SafeCJKParagraph 防止崩溃)
            item_content = [SafeCJKParagraph(str(item), self.styles["List_Body"])]

            # 预读下一项，如果是列表，则是当前项的子列表
            if i + 1 < len(sub_items) and isinstance(sub_items[i + 1], list):
                child_data = sub_items[i + 1]
                # 递归构建子 ListFlowable
                child_flowable = self._build_level(child_data, depth + 1, ordered)
                item_content.append(child_flowable)
                i += 1  # 跳过已处理的子列表

            # 创建 ListItem
            # bulletOffsetY: 微调符号的垂直位置，防止跟文字对不齐
            flowables.append(ListItem(
                item_content,
                bulletColor=text_color,  # 适配深色模式
                value=bullet_char,
                bulletFontName=bullet_font,
                bulletFontSize=10,  # 稍微比正文小一点更精致
                bulletOffsetY=-1  # 视觉微调
            ))

            i += 1

        # 构建 ListFlowable
        return ListFlowable(
            flowables,
            bulletType='bullet',  # 我们通过 ListItem 自定义了 bullet，这里设为 bullet 即可
            start=None,
            # 缩进控制
            leftIndent=18,  # 整体向右缩进
            bulletIndent=0,  # 符号相对于 leftIndent 的位置
            spaceBefore=2,  # 列表项之间的间距
            spaceAfter=2
        )