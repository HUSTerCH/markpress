import copy
import sys

from reportlab.lib import colors, pagesizes
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, PageBreak, Spacer, Table, TableStyle  # 引入 Table
from reportlab.platypus.flowables import HRFlowable

from .renders.code import CodeRenderer
from .renders.heading import HeadingRenderer
from .renders.text import TextRenderer
from .renders.image import ImageRenderer
from .themes import StyleConfig
from .utils import get_font_path


class MarkPressEngine:
    def __init__(self, filename: str, theme_name: str = "academic"):
        self.filename = filename
        print(f"Loading theme: {theme_name}...")
        self.config = StyleConfig.get_pre_build_style(theme_name)

        self._register_fonts()
        self.stylesheet = getSampleStyleSheet()

        # Renderers
        self.text_renderer = TextRenderer(self.config, self.stylesheet)
        self.heading_renderer = HeadingRenderer(self.config, self.stylesheet)
        self.code_renderer = CodeRenderer(self.config, self.stylesheet)
        self.image_renderer = ImageRenderer(self.config, self.stylesheet)

        # self.story 是最终输出列表
        # self.context_stack 用于存储嵌套层级的 (list_obj, available_width)
        self.story = []
        self.context_stack = []
        self.current_story = self.story  # 指针，指向当前正在写入的列表

        # 计算初始可用宽度
        self._init_doc_template()  # 这里会计算 self.page_width 等
        self.avail_width = self.doc.width  # 初始宽度 = 页面有效宽度

    def _register_fonts(self):
        """从 Config 读取字体名，并从 assets 加载"""
        try:
            fonts_to_load = [
                # 正文常规体和斜体
                self.config.fonts.regular,
                self.config.fonts.bold,
                self.config.fonts.regular + "-Italic",
                self.config.fonts.bold + "-Italic",
                # 代码常规体和斜体
                self.config.fonts.code,
                self.config.fonts.code + "-Bold",
                self.config.fonts.code + "-Italic",
                self.config.fonts.code + "-Bold-Italic"
            ]
            for font_name in fonts_to_load:
                with get_font_path(font_name + ".ttf") as font_path:
                    # print(f"加载字体：{font_name}.ttf")
                    pdfmetrics.registerFont(TTFont(font_name, font_path))
            pdfmetrics.registerFontFamily(
                self.config.fonts.regular,
                normal=self.config.fonts.regular,
                bold=self.config.fonts.bold,
                italic=self.config.fonts.regular + "-Italic",
                boldItalic=self.config.fonts.bold + "-Italic",
            )
            pdfmetrics.registerFontFamily(
                self.config.fonts.code,
                normal=self.config.fonts.code,
                bold=self.config.fonts.code + "-Bold",
                italic=self.config.fonts.code + "-Italic",
                boldItalic=self.config.fonts.code + "-Bold-Italic",
            )

        except Exception as e:
            print(f"CRITICAL: Font loading failed - {e}", file=sys.stderr)
            # 字体加载失败是不能容忍的，直接退出或者抛异常
            raise e

    def _init_doc_template(self):
        # 解析页面大小
        ps_map = {
            "A4": pagesizes.A4, "A3": pagesizes.A3,
            "LETTER": pagesizes.LETTER, "LEGAL": pagesizes.LEGAL
        }
        page_size = ps_map.get(self.config.page.size, pagesizes.A4)
        if self.config.page.orientation == "landscape":
            page_size = pagesizes.landscape(page_size)

        self.doc = SimpleDocTemplate(
            self.filename,
            pagesize=page_size,
            leftMargin=self.config.page.margin_left * mm,
            rightMargin=self.config.page.margin_right * mm,
            topMargin=self.config.page.margin_top * mm,
            bottomMargin=self.config.page.margin_bottom * mm,
            title=self.config.meta.name,
            author=self.config.meta.author
        )

        # 计算可用宽度 (用于表格和代码块计算)
        self.avail_width = page_size[0] - (self.config.page.margin_left + self.config.page.margin_right) * mm

    # 引用的处理
    def start_quote(self):
        """进入引用：压栈"""
        self.context_stack.append((self.current_story, self.avail_width))
        new_buffer = []
        self.current_story = new_buffer

        # 读取配置中的缩进值
        q_conf = self.config.styles.quote

        # 缩减可用宽度
        self.avail_width -= (q_conf.left_indent + q_conf.border_width) * mm

    def end_quote(self):
        """退出引用：打包为 Table (修复嵌套引用的长尾巴问题)"""
        if not self.context_stack: return

        # 1. 弹出状态
        quote_content = self.current_story
        parent_story, parent_width = self.context_stack.pop()
        self.current_story = parent_story
        self.avail_width = parent_width

        if not quote_content: return

        # 如果引用内容的最后一个元素是 Spacer，说明它是内层引用留下的尾巴，必须切除。
        while quote_content and isinstance(quote_content[-1], Spacer):
            quote_content.pop()

        # 去除第一段的 spaceBefore
        if quote_content and hasattr(quote_content[0], 'style'):
            first_item = quote_content[0]
            new_style = copy.copy(first_item.style)
            new_style.spaceBefore = 0
            first_item.style = new_style

        # 去除最后一段的 spaceAfter
        if quote_content and hasattr(quote_content[-1], 'style'):
            last_item = quote_content[-1]
            # 如果是 Table (内层引用)，它没有 spaceAfter 属性，忽略即可
            # 如果是 Paragraph，则去尾
            if hasattr(last_item.style, 'spaceAfter'):
                new_style = copy.copy(last_item.style)
                new_style.spaceAfter = 0
                last_item.style = new_style

        # 获取配置
        q_conf = self.config.styles.quote
        border_color = colors.HexColor(q_conf.border_color)

        # 创建容器 Table
        # hAlign='LEFT' 保证引用块紧贴左侧
        t = Table([[quote_content]], colWidths=[self.avail_width], hAlign='LEFT', vAlign='CENTER')

        t.setStyle(TableStyle([
            # 1. 竖线样式
            ('LINEBEFORE', (0, 0), (0, -1), q_conf.border_width, border_color),

            # 2. 缩进控制
            ('LEFTPADDING', (0, 0), (-1, -1), q_conf.left_indent),

            # 3. [关键] 零间距
            # 必须全是 0，否则多层嵌套时 Padding 会累加，导致尾巴越来越长
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 11),

            # 4. 强制顶部对齐 (不要用 MIDDLE)
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),

            # 调试用：如果还有问题，可以把下面这行解开看格子
            # ('GRID', (0, 0), (-1, -1), 0.5, colors.red),
        ]))

        # 将引用块加入父级
        self.current_story.append(t)

        # 在引用块外部添加 Spacer
        # 这个 Spacer 作用于当前层级之后，但会被上一层切除
        self.current_story.append(Spacer(1, 4 * mm))

    def add_heading(self, text: str, level: int):
        flowables = self.heading_renderer.render(text, level)
        self.current_story.extend(flowables)

    def add_text(self, xml_text: str):
        # 检查当前是否在引用中 (通过栈是否为空判断)
        is_in_quote = len(self.context_stack) > 0

        if is_in_quote:
            # 使用配置中的引用文字颜色
            q_color = self.config.styles.quote.text_color
            # 嵌套一层 font 标签来变色
            # 如果 xml_text 里已经有了 color 设置，内层会覆盖外层，这是合理的
            xml_text = f'<font color="{q_color}">{xml_text}</font>'
        flowables = self.text_renderer.render(xml_text)
        self.current_story.extend(flowables)

    # 分割线
    def add_horizontal_rule(self):
        """添加水平分隔线"""
        # 复用主题中的边框颜色 (self.config.colors.border)
        try:
            line_color = colors.HexColor(self.config.colors.border)
        except:
            line_color = colors.lightgrey

        # 创建分隔线
        # width="100%": 占满当前可用宽度（会自动适应引用块内的宽度）
        # thickness=1: 线条粗细
        # lineCap='round': 圆头线端
        hr = HRFlowable(
            width="100%",
            thickness=1,
            lineCap='round',
            color=line_color,
            spaceBefore=4 * mm,  # 线条上方的留白
            spaceAfter=4 * mm,  # 线条下方的留白
            hAlign='CENTER',
            vAlign='CENTER',
            dash=None  # 如果想做虚线，可以设为 [2, 4]
        )

        self.current_story.append(hr)

    def add_code(self, code: str, language: str = None):
        # 关键：传入当前的 self.avail_width，这样嵌套在引用里的代码块会自动变窄
        flowables = self.code_renderer.render(code, language, avail_width=self.avail_width)
        self.current_story.extend(flowables)

    def add_image(self, image_path: str, alt_text: str = ""):
        """添加图片"""
        flowables = self.image_renderer.render(image_path, alt_text, avail_width=self.avail_width)
        self.current_story.extend(flowables)

    def add_spacer(self, height_mm: float):
        self.current_story.append(Spacer(1, height_mm * mm))

    def add_page_break(self):
        self.current_story.append(PageBreak())

    def save(self):
        # print(f"Generating PDF: {self.filename}...")
        # print(self.story)
        # 去除尾巴的空格
        if self.story[-1] and isinstance(self.story[-1], Spacer):
            self.story.pop()
        try:
            self.doc.build(self.story)  # 根 story
            print("Done.")
        except Exception as e:
            print(f"Error building PDF: {e}")
            raise e
