import importlib.resources
import os
import re
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


def _get_raw_text(tokens: list) -> str:
    """递归提取 tokens 中的纯文本，剥离所有嵌套结构"""
    res = ""
    if not tokens: return res
    for tok in tokens:
        if 'raw' in tok:
            res += tok['raw']
        if 'children' in tok:
            res += _get_raw_text(tok['children'])
    return res


def _slugify(text: str) -> str:
    """
    1:1 完美复刻 GitHub 风格的锚点 ID 生成算法
    """
    # 1. 转小写
    text = text.lower()

    # 2. 将所有空格精确替换为连字符 (不合并连续空格)
    text = text.replace(' ', '-')

    # 3. 移除除了字母、数字、汉字、连字符和下划线之外的所有字符
    # \w 包含字母数字下划线, \u4e00-\u9fff 包含汉字, - 是连字符
    text = re.sub(r'[^\w\u4e00-\u9fff-]', '', text)

    return text


def replace_to_twemoji(chars, data_dict):
    # Twemoji 的文件命名法：Unicode Hex 连字符拼接，并剔除 0xfe0f (不可见变体选择器)
    hex_str = '-'.join(f"{ord(c):x}" for c in chars if ord(c) != 0xfe0f)
    # 使用 jsdelivr CDN 提供的 twemoji 标准图库 (PNG 格式渲染最快)
    url = f"https://cdn.jsdelivr.net/gh/jdecked/twemoji@latest/assets/72x72/{hex_str}.png"

    # 高度设为 12，valign 设为 -2 恰好可以与中文字体基线完美对齐
    return f'<img src="{url}" width="12.01" height="12.01" valign="-2.01" />'

def strip_front_matter(md_text: str) -> str:
    """
    硬核防线：精准切除文件头部的 YAML Front Matter。
    使用 \A 确保绝对只匹配文件的第一行，绝不误伤正文里的 Markdown 分割线。
    """
    pattern = re.compile(r'\A---\n.*?\n---\n', re.DOTALL)
    return pattern.sub('', md_text)