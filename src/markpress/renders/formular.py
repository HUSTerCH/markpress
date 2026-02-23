# 公式，包含行内和行间
import os
import tempfile
from typing import Any, List

import matplotlib.pyplot as plt
from PIL import Image as PILImage  # 用于精确获取像素尺寸
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, Spacer, Flowable

from .base import BaseRenderer
from ..utils import APP_TMP

# # [Global Cache]
# # Matplotlib 渲染开销极大，必须缓存已渲染的公式
# # Key: (latex_str, fontsize), Value: (image_path, width_pt, height_pt)
# _FORMULA_CACHE = {}


class FormulaRenderer(BaseRenderer):
    def render(self, data: Any, **kwargs) -> List[Flowable]:
        pass

    def render_block(self, latex: str, **kwargs):
        """
        渲染行间公式 (Block Math)
        Returns: [Image, Spacer]
        """
        try:
            # 渲染图片 (行间公式字号稍大，设为 14pt)
            avail_width = kwargs.get('avail_width', 160 * mm)
            avail_height = kwargs.get('avail_height', 240 * mm)
            # 行间公式通常用 DPI 300 保证清晰度
            img_path, w, h = self._generate_image(latex, fontsize=14, dpi=300)

            # 关键：给高度留安全边（避免碰到底部/上部间距+Spacer）
            safety = 10 * mm
            max_w = avail_width
            max_h = max(10, avail_height - safety)
            scale = min(max_w / w, max_h / h, 1.0)
            w *= scale
            h *= scale

            img = Image(img_path, width=w, height=h)
            img.hAlign = 'CENTER'

            return [img, Spacer(1, 4 * mm)]

        except Exception as e:
            # 降级处理：显示显眼的红色错误信息
            error_text = f"<font color='red' size='10'>[Formula Error: {latex}]</font>"
            return [Paragraph(error_text, self.styles["Body_Text"]), Spacer(1, 4 * mm)]

    def render_inline(self, latex: str) -> str:
        """
        渲染行内公式 (Inline Math)
        Returns: 嵌入 Paragraph 的 <img/> 标签字符串
        """
        try:
            # 获取正文字号 (保证公式大小与文字匹配)
            body_font_size = self.config.styles.body.font_size

            # 渲染图片
            img_path, w, h = self._generate_image(latex, fontsize=body_font_size, dpi=300)

            # 计算垂直对齐 (Vertical Alignment)
            valign = f"-{h * 0.25}"
            # 4. 返回 XML 标签
            return f'<img src="{img_path}" width="{w}" height="{h}" valign="{valign}"/>'

        except Exception as e:
            # 降级：显示红色 LaTeX 源码，转义 latex 中的特殊字符，防止 XML 错误
            safe_latex = latex.replace('<', '&lt;').replace('>', '&gt;')
            return f"<font color='red'>${safe_latex}$</font>"

    def _generate_image(self, latex: str, fontsize: float, dpi: int = 300):
        """
        核心渲染引擎 (Matplotlib -> Temp File)
        """
        # cache_key = (latex, fontsize)
        # if cache_key in _FORMULA_CACHE:
        #     return _FORMULA_CACHE[cache_key]

        # 配置 Matplotlib，stix' 字体风格最接近标准 LaTeX
        plt.rc('mathtext', fontset='stix')

        # 创建微型画布，figsize 设得很小，完全依赖 bbox_inches='tight' 自动撑开
        fig = plt.figure(figsize=(0.01, 0.01))

        # 绘制文字
        fig.text(0, 0, f"${latex}$", fontsize=fontsize)

        # 保存到临时文件，使用 tempfile 生成唯一路径，且不自动删除 (ReportLab 读取需要文件存在)
        # to do: 在生产环境中，这些临时文件应该在程序结束时清理，或者定期清理 /tmp
        # 已经完成to do
        fd, path = tempfile.mkstemp(suffix=".png",dir=APP_TMP)
        os.close(fd)  # 关闭文件描述符，释放给 plt 使用

        # 渲染保存，transparent=True 保证背景透明，融合纸张颜色，pad_inches=0.02 留极少量的白边，防止切掉积分号等大符号的边缘
        plt.axis('off')
        plt.savefig(path, format='png', bbox_inches='tight', pad_inches=0.02, dpi=dpi, transparent=True)
        plt.close(fig)  # 必须关闭，防止内存泄漏

        # 计算物理尺寸，Matplotlib 仅仅保存了像素，我们需要将其换算回 PDF 的 Points 单位
        # 公式：Point = Pixel * 72 / DPI
        with PILImage.open(path) as pi:
            px_w, px_h = pi.size

        pt_w = px_w * 72 / dpi
        pt_h = px_h * 72 / dpi

        # 存入缓存
        result = (path, pt_w, pt_h)
        # _FORMULA_CACHE[cache_key] = result
        return result