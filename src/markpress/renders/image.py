import os
from reportlab.platypus import Image, Spacer
from reportlab.lib.units import mm
from .base import BaseRenderer


class ImageRenderer(BaseRenderer):
    """图片渲染器"""
    def render(self, image_path: str, alt_text: str = "", **kwargs):
        # 获取可用宽度
        avail_width = kwargs.get('avail_width', 160 * mm)
        # 检查图片文件是否存在
        if not os.path.exists(image_path):
            print(f"警告: 图片文件不存在: {image_path}")
            return []
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
                Spacer(1, 3 * mm),  # 图片前的间距
                img,
                Spacer(1, 3 * mm)   # 图片后的间距
            ]
        except Exception as e:
            print(f"错误: 无法加载图片 {image_path}: {e}")
            return []
