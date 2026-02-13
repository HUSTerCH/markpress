import importlib.resources
from contextlib import contextmanager
from pathlib import Path

@contextmanager
def get_font_path(filename: str):
    """获取 assets/fonts 下文件的绝对路径。"""
    # 对应 src/markpress/assets/fonts 目录
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


