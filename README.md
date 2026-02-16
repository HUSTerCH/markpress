# Markpress

一个高质量的 Markdown 转 PDF 转换器，基于 Python 实现。支持主题配置、中英文混排、代码高亮、引用块嵌套等特性。

## 项目结构

```
markpress/
├── src/markpress/            # 核心包
│   ├── core.py               # PDF 引擎（MarkPressEngine）
│   ├── converter.py          # Markdown → PDF 转换入口
│   ├── themes.py             # 主题配置解析（dataclass + JSON）
│   ├── utils.py              # 字体/主题资源路径工具
│   ├── renders/              # 渲染器模块
│   │   ├── base.py           # 渲染器抽象基类
│   │   ├── text.py           # 正文渲染（富文本 XML → ReportLab Paragraph）
│   │   ├── heading.py        # 标题渲染（H1–H4）
│   │   ├── code.py           # 代码块渲染（Pygments 高亮 + CJK 回退）
│   │   ├── image.py          # 图片渲染（支持相对/绝对路径，自动缩放）
│   │   ├── table.py          # 表格（待实现）
│   │   ├── list.py           # 列表（待实现）
│   │   └── formular.py       # 公式（待实现）
│   └── assets/themes/        # 预置主题 JSON
│       ├── academic.json     # 学术风格
│       └── modern_screen.json # 深色屏显风格
│
├── managePDF/                # 独立的 PDF 编写工具（不依赖 Markdown 解析）
│   ├── pypdf_writer.py       # PyPDFWriter 封装类
│   └── main.py               # 全功能演示脚本
│
├── tests/                    # 测试与调试脚本
├── pyproject.toml            # Poetry 项目配置
└── poetry.lock
```

## 核心功能

### Markdown → PDF 转换

通过 `converter.py` 将 Markdown 文件转换为 PDF：

1. 使用 **mistune** 将 Markdown 解析为 AST
2. 遍历 AST 节点，调用 `MarkPressEngine` 的对应方法生成 PDF 元素
3. 使用 **ReportLab** 构建并输出最终 PDF

目前已支持的 Markdown 元素：标题、段落（加粗/斜体/链接/行内代码等富文本）、代码块（Pygments 语法高亮）、引用块（多层嵌套）、分隔线、图片（支持相对/绝对路径，自动缩放适配页面）。

```python
from markpress.converter import convert_markdown_file

convert_markdown_file("input.md", "output.pdf", theme="academic")
```

### 主题系统

主题以 JSON 文件定义，通过 `themes.py` 中的 dataclass 体系解析，涵盖：

- **页面**：纸张尺寸（A4/A3 等）、边距
- **字体**：正文字体（HarmonyOS Sans）、代码字体（JetBrains Mono）
- **样式**：正文、标题（H1–H4）、代码块、表格、引用块各自的字号/颜色/间距/对齐等

### managePDF 子模块

`managePDF/` 提供了一个独立于 Markdown 解析流程的 `PyPDFWriter` 类，可通过 Python API 直接编写 PDF，支持标题、正文、多级列表、代码块、表格、LaTeX 公式等。适用于需要程序化生成 PDF 文档的场景。详见 [managePDF/README.md](managePDF/README.md)。

## 技术栈

| 组件 | 用途 |
|------|------|
| ReportLab | PDF 生成引擎 |
| mistune | Markdown 解析（AST 模式） |
| Pygments | 代码语法高亮 |
| matplotlib | LaTeX 公式渲染 |
| BeautifulSoup4 | 富文本 HTML 清洗与转换 |

## 环境要求

- Python ≥ 3.10
- 依赖安装：`poetry install`
