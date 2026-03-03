import os
from reportlab.platypus import Image, Spacer,Paragraph
from reportlab.lib.units import mm
from .base import BaseRenderer
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.lib.styles import ParagraphStyle
import tempfile
import urllib.request
from PIL import Image as PILImage
from ..utils import APP_TMP

# 本地文档转换工具，允许加载高分辨率图片
PILImage.MAX_IMAGE_PIXELS = None


class ImageRenderer(BaseRenderer):

    def __init__(self, config, stylesheet):
        super().__init__(config, stylesheet)
        self._init_paragraph_style()

    def _init_paragraph_style(self):
        # 普通的段落样式
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

    # 图片渲染器
    def render(self, image_path: str, alt_text: str = "", **kwargs):
        avail_width = kwargs.get('avail_width', 160 * mm)

        # 在线图片：下载到本地临时文件
        if image_path.startswith(('http://', 'https://')):
            local_path = self._download_image(image_path)
            if not local_path:
                print(f"警告: 无法下载图片: {image_path}")
                return []
            image_path = local_path

        if not os.path.exists(image_path):
            print(f"警告: 图片文件不存在或无法访问: {image_path}")
            return [Paragraph(f"<b><font color='red'>加载图片{alt_text}失败</font></b>",self.styles["Body_Text"])]
        try:
            img = Image(image_path)
            # 获取原始尺寸
            img_width = img.imageWidth
            img_height = img.imageHeight
            # 计算缩放比例，确保图片不超过可用宽度，同时限制最大高度为页面的 60%（约 170mm for A4）
            max_height = 170 * mm

            if img_width > avail_width:
                # 按宽度缩放
                scale = avail_width / img_width
                img.drawWidth = avail_width
                img.drawHeight = img_height * scale
            else:
                # 保持原始尺寸
                img.drawWidth = img_width
                img.drawHeight = img_height
            # 如果缩放后高度仍然过大，再按高度缩放
            if img.drawHeight > max_height:
                scale = max_height / img.drawHeight
                img.drawHeight = max_height
                img.drawWidth = img.drawWidth * scale
            img.hAlign = 'CENTER'
            return [
                Spacer(1, 6 * mm),  # 图片前的间距
                img,
                # Spacer(1, 3 * mm)   # 图片后的间距
            ]
        except Exception as e:
            print(f"错误: 无法加载图片 {image_path}: {e}")
            return []

    @staticmethod
    def _download_image(url: str) -> str:
        """下载在线图片到临时文件，返回本地路径；失败返回 None"""
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read()
            # 从 URL 提取扩展名，默认 .png
            suffix = os.path.splitext(url.split('?')[0])[-1] or '.png'
            fd, path = tempfile.mkstemp(suffix=suffix, dir=APP_TMP)
            os.write(fd, data)
            os.close(fd)
            return path
        except Exception as e:
            print(f"[Warn] 下载图片失败 {url}: {e}")
            return None
