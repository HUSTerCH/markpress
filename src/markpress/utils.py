import importlib.resources
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path


APP_TMP = os.path.join(tempfile.gettempdir(), "markpress")

@contextmanager
def get_font_path(filename: str):
    """获取 assets/fonts 下文件的绝对路径。"""
    # 对应 src/markpress/assets/fonts 目录
    # 下同
    ref = importlib.resources.files('markpress.assets.fonts') / filename
    with importlib.resources.as_file(ref) as path:
        if not path.exists():
            raise FileNotFoundError(f"Font missing: {filename} in {path}")
        yield str(path)


@contextmanager
def get_theme_path(filename: str):
    ref = importlib.resources.files('markpress.assets.themes') / filename
    with importlib.resources.as_file(ref) as path:
        if not path.exists():
            raise FileNotFoundError(f"Theme missing: {filename} in {path}")
        yield str(path)


@contextmanager
def get_katex_path():
    ref = importlib.resources.files('markpress.assets') / 'katex'
    with importlib.resources.as_file(ref) as path:
        if not path.exists():
            raise FileNotFoundError(f"KaTeX assets directory missing at: {path}")
        yield str(path)


def clear_temp_files():
    print(f"清理临时文件夹：{APP_TMP}")
    for f in os.listdir(APP_TMP):
        if f.startswith("tmp") and f.endswith(".png"):
            try:
                os.remove(os.path.join(APP_TMP, f))
            except:
                pass
