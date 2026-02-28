import importlib.resources
import os
import re
import tempfile
from contextlib import contextmanager

from bs4 import BeautifulSoup, Tag, Comment

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


@contextmanager
def get_twemoji_path():
    ref = importlib.resources.files('markpress.assets') / 'twemoji_72'
    with importlib.resources.as_file(ref) as path:
        if not path.exists():
            raise FileNotFoundError(f"twemoji assets directory missing at: {path}")
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

def replace_to_local_twemoji(chars, data_dict):
    hex_str = '-'.join(f"{ord(c):x}" for c in chars if ord(c) != 0xfe0f)
    with get_twemoji_path() as twemoji_path:
        local_img_path = os.path.join(twemoji_path, f"{hex_str}.png")

    # 如果本地没这个表情（比如刚出的新 Emoji），降级为空或占位符
    if not os.path.exists(local_img_path):
        return ""  # 或者返回一个默认的问号图片路径

    return f'<img src="{local_img_path}" width="12.01" height="12.01" valign="-2.01" />'

def strip_front_matter(md_text: str) -> str:
    """
    硬核防线：精准切除文件头部的 YAML Front Matter。
    使用 \A 确保绝对只匹配文件的第一行，绝不误伤正文里的 Markdown 分割线。
    """
    pattern = re.compile(r'\A---\n.*?\n---\n', re.DOTALL)
    return pattern.sub('', md_text)


def _optimize_ast_html_blocks(tokens: list) -> list:
    """
    AST 核心中间件：
    1. 缝合被 Markdown 规范错切的 HTML 碎块。
    2. 使用 DOM 树解析，按“根 HTML 标签”重新精准切割。
    """
    if not tokens:
        return []

    optimized = []
    html_buffer = []

    def flush_html_buffer():
        """执行重组与切割手术"""
        if not html_buffer:
            return

        merged_html = "".join(html_buffer)

        # 核心逻辑：利用 BS4 的容错解析能力，把字符串还原为严格的 DOM 树
        soup = BeautifulSoup(merged_html, 'html.parser')

        # 遍历根节点
        for child in soup.contents:
            if isinstance(child, Tag):
                # 完整的 HTML 标签块
                optimized.append({'type': 'block_html', 'raw': str(child)})
            elif isinstance(child, Comment):
                # 拦截注释对象，手动复原 外壳
                # 这样后续的 _process_block_html 里的正则清理就能精准定位并安全销毁它，而不会污染正文
                optimized.append({'type': 'block_html', 'raw': f''})
            else:
                # 纯文本或其他字符
                text = str(child).strip()
                if text:
                    optimized.append({'type': 'block_html', 'raw': text})

        html_buffer.clear()

    for tok in tokens:
        t_type = tok.get('type')

        if t_type == 'block_html':
            html_buffer.append(tok.get('raw', ''))
        elif t_type == 'blank_line' and html_buffer:
            # 维持收集状态
            html_buffer.append('\n\n')
        else:
            # 遇到正规 Markdown 节点，清空并结算缓冲池
            flush_html_buffer()

            # 递归处理子节点
            if 'children' in tok and tok['children']:
                tok['children'] = _optimize_ast_html_blocks(tok['children'])

            optimized.append(tok)

    # 循环结束，最后结算一次
    flush_html_buffer()

    return optimized