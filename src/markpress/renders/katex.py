from pathlib import Path
from typing import Any, List
import os
import tempfile

from playwright.sync_api import sync_playwright
from reportlab.platypus import Flowable

from .base import BaseRenderer
from ..utils import get_katex_path, APP_TMP


class KatexRenderer(BaseRenderer):
    def render(self, data: Any, **kwargs) -> List[Flowable]:
        pass

    def __init__(self, config, stylesheet):
        super().__init__(config, stylesheet)

        with get_katex_path() as katex_root:
            self.assets_dir = Path(katex_root)
            self.js_path = self.assets_dir / "katex.min.js"
            self.css_path = self.assets_dir / "katex.min.css"

            if not self.js_path.exists():
                raise FileNotFoundError(f"KaTeX JS missing: {self.js_path}")

        # 2. 初始化 Playwright (单例模式，避免每个公式都重启浏览器)
        self.playwright = None
        self.browser = None
        self.page = None
        self._init_browser()

    def _init_browser(self):
        print("Initializing KaTeX Rendering Engine (Playwright)...")
        self.playwright = sync_playwright().start()

        browser_channels = ["chrome", "msedge", None]

        self.browser = None

        # --- [阶段一]：尝试利用本地已安装的浏览器 ---
        for channel in browser_channels:
            try:
                # print(f"Trying to launch browser: {channel if channel else 'Bundled Chromium'}...")
                self.browser = self.playwright.chromium.launch(
                    headless=True,
                    channel=channel
                )
                print(f"[MarkPress] Successfully launched: {channel if channel else 'Bundled Chromium'}")
                break  # 成功启动，跳出循环
            except Exception:
                # 当前 channel 启动失败，继续尝试下一个
                continue

        # --- [阶段二]：如果所有本地浏览器都失败，执行自动安装 ---
        if self.browser is None:
            print("[MarkPress] No suitable browser found.")
            print("[MarkPress] Auto-installing Playwright Chromium kernel (approx 130MB)...")

            try:
                import sys, subprocess
                # 强制使用国内源，提高成功率
                env = os.environ.copy()
                env["PLAYWRIGHT_DOWNLOAD_HOST"] = "https://npmmirror.com/mirrors/playwright/"

                subprocess.check_call(
                    [sys.executable, "-m", "playwright", "install", "chromium"],
                    env=env
                )

                print("[MarkPress] Browser kernel installed successfully.")
                # 安装完后，再次尝试启动 (不带 channel，使用刚下载的 bundled chromium)
                self.browser = self.playwright.chromium.launch(headless=True)

            except Exception as e:
                print(f"[CRITICAL] Failed to launch KaTeX engine: {e}")
                print("Hint: You can try running 'playwright install chromium' manually.")
                raise e

        self.page = self.browser.new_page(device_scale_factor=3)

        # 通过 API 注入引用资源,先设置一个空的骨架 HTML
        self.page.set_content("""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { margin: 0; padding: 0; background: transparent; }
                #container { display: inline-block; padding: 1px; }
            </style>
        </head>
        <body>
            <div id="container"></div>
        </body>
        </html>
        """)

        # 注入 CSS (阻塞式)
        self.page.add_style_tag(path=str(self.css_path))

        # 注入 JS (阻塞式)Playwright 会自动处理文件读取和执行等待
        self.page.add_script_tag(path=str(self.js_path))

        # 等待 katex 对象在 window 中可用,如果这一步超时，说明 JS 文件本身有问题（路径错或文件坏）
        try:
            self.page.wait_for_function("() => typeof katex !== 'undefined'", timeout=5000)
            print("KaTeX Engine Loaded Successfully.")
        except Exception as e:
            print(f"CRITICAL: KaTeX JS failed to load. Path: {self.js_path}")
            raise e

    def render_image(self, latex: str, is_block: bool = False):
        """
        调用 JS 渲染 LaTeX，并截图
        """
        try:
            # 准备 JS 代码
            # throwOnError: false 防止 JS 报错导致程序崩
            display_mode = "true" if is_block else "false"
            js_script = f"""
                katex.render(String.raw`{latex}`, document.getElementById('container'), {{
                    displayMode: {display_mode},
                    throwOnError: false
                }});
            """

            # 执行渲染
            self.page.evaluate(js_script)

            # 等待容器尺寸稳定 (KaTeX 渲染很快，通常不需要 wait，但为了保险)
            # 获取元素的 bounding box
            locator = self.page.locator("#container")
            box = locator.bounding_box()

            if not box or box['width'] == 0:
                raise ValueError("Rendered empty box")

            # 截图，返回 bytes，path=None 表示直接返回二进制
            png_bytes = locator.screenshot(type="png", omit_background=True)

            # 5. 清理 DOM 以便下次使用
            self.page.evaluate("document.getElementById('container').innerHTML = ''")

            # 6. 计算 PDF 中的尺寸 (Point)
            # Playwright 截图受 device_scale_factor 影响
            # box['width'] 是 CSS 像素，ReportLab 使用 Points (1 CSS px ≈ 0.75 pt)
            # 但这里我们直接用 box 尺寸即可，因为浏览器默认 96DPI
            # PDF Point = px * 72 / 96 = px * 0.75
            width_pt = box['width'] * 0.75
            height_pt = box['height'] * 0.75

            return png_bytes, width_pt, height_pt

        except Exception as e:
            print(f"KaTeX Render Error Happens: {e}")
            return None, 0, 0

    def render_svg_url_to_png(self, url: str):
        """
        光栅化：让 Chromium 打开 SVG 链接并截图为 PNG
        """
        if not self.browser or not self.page:
            return None, 0, 0

        try:
            # print(f"Rasterizing SVG: {url}")
            # 直接让浏览器访问这个 SVG 链接或 API
            self.page.goto(url, wait_until="networkidle")

            # 定位页面上的 svg 元素 (通常浏览器直接打开 svg 文件，根节点就是 svg)
            locator = self.page.locator("svg").first
            box = locator.bounding_box()

            if not box:
                return None, 0, 0

            # 截图为 PNG 内存流
            png_bytes = locator.screenshot(type="png", omit_background=True)

            # 转换为 ReportLab 的 Point 单位 (1px ≈ 0.75pt)
            width_pt = box['width'] * 0.75
            height_pt = box['height'] * 0.75

            return png_bytes, width_pt, height_pt

        except Exception as e:
            print(f"[Warn] Failed to rasterize SVG {url}: {e}")
            return None, 0, 0

    def render_svg_url_to_file(self, url: str):
        """光栅化 SVG 并保存为临时文件供行内标签调用"""

        png_bytes, w, h = self.render_svg_url_to_png(url)
        if not png_bytes:
            return None, 0, 0

        # 写入临时文件
        fd, path = tempfile.mkstemp(suffix=".png",dir=APP_TMP)
        os.write(fd, png_bytes)
        os.close(fd)

        return path, w, h

    def close(self):
        print("关闭Katex渲染器.")
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
