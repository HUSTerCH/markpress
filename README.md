# Markpress

一个高质量的 Markdown 转 PDF 转换器，基于 Python 实现。支持主题配置、中英文混排、代码高亮、表格、数学公式、引用块嵌套等特性。

## 快速使用

### 环境搭建

建议Python ≥ 3.10，使用poetry安装依赖，poetry的安装方法请参考[poetry官方文档](https://python-poetry.org/docs/)

```bash
poetry install
```

### 命令行转换

```bash
# 基本用法（输出与输入同目录同名）
markpress convert input.md

# 指定输出路径和主题
markpress convert input.md -o output.pdf -t github

# 开启调试模式
markpress convert input.md --debug
```

可用主题：`academic`（默认）、`lark`、`github`、`vue`

### Web 界面

```bash
# 启动 Web 服务器（默认 http://127.0.0.1:8080）
markpress serve

# 自定义地址和端口
markpress serve --host 0.0.0.0 --port 9090
```

在浏览器中打开后，可上传 Markdown 文件及引用的图片，选择主题、页面方向、纸张大小，实时预览并下载 PDF。

### Python API

```python
from markpress.converter import convert_markdown_file

convert_markdown_file("input.md", "output.pdf", theme="academic")
```

## 核心功能

### Markdown → PDF 转换

通过 `converter.py` 将 Markdown 文件转换为 PDF：

1. 使用 **mistune** 将 Markdown 解析为 AST
2. 遍历 AST 节点，调用 `MarkPressEngine` 的对应方法生成 PDF 元素
3. 使用 **ReportLab** 构建并输出最终 PDF

已支持的 Markdown 元素：标题（H1–H6）、段落（加粗/斜体/链接/行内代码等富文本）、代码块（Pygments 语法高亮）、表格（标准/管道/HTML 三种格式，含 colspan 和行背景色）、有序/无序列表（含嵌套）、数学公式（行内/行间 LaTeX，KaTeX 优先渲染）、引用块（多层嵌套）、分隔线、图片（支持相对/绝对路径，自动缩放适配页面）。

### 主题系统

主题以 JSON 文件定义，通过 `themes.py` 中的 dataclass 体系解析，涵盖：

- **页面**：纸张尺寸（A4/A3 等）、边距
- **字体**：正文字体（HarmonyOS Sans / WenYuan）、代码字体（JetBrains Mono）
- **样式**：正文、标题（H1–H6）、代码块、表格、引用块各自的字号/颜色/间距/对齐等

## 项目结构

```
markpress/
├── src/markpress/            # 核心包
│   ├── core.py               # PDF 引擎（MarkPressEngine）
│   ├── converter.py          # Markdown → PDF 转换入口
│   ├── cli.py                # 命令行接口入口（convert / serve 子命令）
│   ├── server.py             # Web 服务器（FastAPI + Uvicorn）
│   ├── themes.py             # 主题配置解析（dataclass + JSON）
│   ├── utils/                # 工具模块
│   │   ├── utils.py          # 字体/主题资源路径工具、front matter 剥离等
│   │   └── fonts_manager.py  # 字体注册与加载管理
│   ├── renders/              # 渲染器模块
│   │   ├── base.py           # 渲染器抽象基类
│   │   ├── text.py           # 正文渲染（富文本 XML → ReportLab Paragraph）
│   │   ├── heading.py        # 标题渲染（H1–H6）
│   │   ├── code.py           # 代码块渲染（Pygments 高亮 + CJK 回退）
│   │   ├── image.py          # 图片渲染（支持相对/绝对路径，自动缩放）
│   │   ├── table.py          # 表格渲染（含 colspan、行背景色）
│   │   ├── list.py           # 有序/无序列表（含嵌套）
│   │   ├── formular.py       # LaTeX 公式渲染（Matplotlib）
│   │   └── katex.py          # KaTeX 公式渲染（Playwright + Chromium）
│   └── assets/               # 静态资源
│       ├── web/              # Web 前端界面
│       │   └── index.html    # 单页面应用（Tailwind CSS + Alpine.js）
│       ├── themes/           # 预置主题 JSON
│       │   ├── academic.json # 学术风格
│       │   ├── lark.json     # Lark 飞书风格
│       │   ├── github.json   # GitHub 风格
│       │   └── vue.json      # Vue 文档风格
│       └── fonts/            # 内置字体（HarmonyOS Sans、JetBrains Mono、WenYuan 等）
│
├── managePDF/                # 独立的 PDF 编写工具（不依赖 Markdown 解析）
│   ├── pypdf_writer.py       # PyPDFWriter 封装类
│   └── main.py               # 全功能演示脚本
│
├── tests/                    # 测试与调试脚本
├── pyproject.toml            # Poetry 项目配置
└── poetry.lock
```

