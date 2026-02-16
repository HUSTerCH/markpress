from reportlab.platypus import Paragraph, Spacer
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY

from .base import BaseRenderer


class HeadingRenderer(BaseRenderer):
    def render(self, text: str, level: int = 1, **kwargs):
        # 限制层级
        level = max(1, min(4, level))

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