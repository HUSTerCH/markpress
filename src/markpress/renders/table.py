from typing import Any, List, Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Flowable, Paragraph, Spacer, Table, TableStyle

from .base import BaseRenderer


class TableRenderer(BaseRenderer):
    """Markdown 表格渲染器，将解析后的表格数据转为 ReportLab Table"""

    ALIGN_MAP = {"left": TA_LEFT, "center": TA_CENTER, "right": TA_RIGHT}

    def __init__(self, config, stylesheet):
        super().__init__(config, stylesheet)
        self._init_styles()

    def _init_styles(self):
        if "Table_Header" not in self.styles:
            t_conf = self.config.styles.table
            self.styles.add(ParagraphStyle(
                name="Table_Header",
                fontName=self.config.fonts.bold,
                fontSize=self.config.styles.body.font_size,
                leading=self.config.styles.body.font_size * 1.4,
                textColor=colors.HexColor(t_conf.header_text),
                wordWrap='CJK',
                splitLongWords=True,
            ))
        if "Table_Cell" not in self.styles:
            self.styles.add(ParagraphStyle(
                name="Table_Cell",
                fontName=self.config.fonts.regular,
                fontSize=self.config.styles.body.font_size,
                leading=self.config.styles.body.font_size * 1.4,
                textColor=colors.HexColor(self.config.colors.text_primary),
                wordWrap='CJK',
                splitLongWords=True,
            ))

    def render(self, data: Any, **kwargs) -> List[Flowable]:
        """
        渲染表格
        :param data: dict with keys 'header', 'body', 'aligns'
            - header: List[str]  表头单元格 XML 文本
            - body: List[List[str]]  每行的单元格 XML 文本
            - aligns: List[Optional[str]]  每列的对齐方式 ('left'/'center'/'right'/None)
        :param kwargs: avail_width 可用宽度
        """
        header: List[str] = data.get("header", [])
        body: List[List[str]] = data.get("body", [])
        aligns: List[Optional[str]] = data.get("aligns", [])
        avail_width = kwargs.get("avail_width", 160 * mm)

        if not header and not body:
            return []

        num_cols = len(header) if header else (len(body[0]) if body else 0)
        if num_cols == 0:
            return []

        # 等宽分配列宽
        col_width = avail_width / num_cols
        col_widths = [col_width] * num_cols

        # 构建 Paragraph 矩阵
        table_data = []

        if header:
            header_row = []
            for i, cell_text in enumerate(header):
                style = self._cell_style("Table_Header", aligns, i)
                header_row.append(Paragraph(cell_text or "", style))
            table_data.append(header_row)

        for row in body:
            data_row = []
            for i, cell_text in enumerate(row):
                style = self._cell_style("Table_Cell", aligns, i)
                data_row.append(Paragraph(cell_text or "", style))
            table_data.append(data_row)

        if not table_data:
            return []

        t = Table(table_data, colWidths=col_widths, hAlign='LEFT')

        # 构建样式命令
        t_conf = self.config.styles.table
        header_bg = colors.HexColor(t_conf.header_bg)
        row_even = colors.HexColor(t_conf.row_bg_even)
        row_odd = colors.HexColor(t_conf.row_bg_odd)
        grid_color = colors.HexColor(t_conf.grid_color)

        style_cmds = [
            ('GRID', (0, 0), (-1, -1), 0.5, grid_color),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]

        # 表头背景
        if header:
            style_cmds.append(('BACKGROUND', (0, 0), (-1, 0), header_bg))

        # 数据行斑马纹，起始行号取决于是否有表头
        data_start = 1 if header else 0
        total_rows = len(table_data)
        for row_idx in range(data_start, total_rows):
            bg = row_even if (row_idx - data_start) % 2 == 0 else row_odd
            style_cmds.append(('BACKGROUND', (0, row_idx), (-1, row_idx), bg))

        t.setStyle(TableStyle(style_cmds))

        return [Spacer(1, 2 * mm), t, Spacer(1, 4 * mm)]

    def _cell_style(self, base_name: str, aligns: List[Optional[str]], col_idx: int) -> ParagraphStyle:
        """根据列对齐方式返回适配的 ParagraphStyle（命中缓存或动态创建）"""
        align_str = aligns[col_idx] if col_idx < len(aligns) and aligns[col_idx] else "left"
        cache_name = f"{base_name}_{align_str}"

        if cache_name in self.styles:
            return self.styles[cache_name]

        base = self.styles[base_name]
        aligned = ParagraphStyle(
            name=cache_name,
            parent=base,
            alignment=self.ALIGN_MAP.get(align_str, TA_LEFT),
        )
        self.styles.add(aligned)
        return aligned
