# Python直接操作写PDF封装类的使用说明

## 环境要求

进入`requirements.txt`查看所需要的库和版本，可直接运行`pip install -r requiremets.txt`安装所有必须要的库

## 开始

项目结构要求：由于`pypdf_writer.py`代码中存在硬编码，所以请务必保证项目结构如下所示：

```plaintext
SomeWhereAFolder/
├── pypdf_writer.py         # 封装库文件
│
├── HarmonyOS_Sans/         # [必须] 中文字体目录
│   ├── HarmonyOS_Sans_SC_Regular.ttf
│   └── HarmonyOS_Sans_SC_Bold.ttf
│
└── JetBrains_Mono/         # [必须] 代码字体目录
    └── JetBrainsMono-Regular.ttf
```

初始化文件夹

```python
from pypdf_writer import PyPDFWriter
from pathlib import Path

# 初始化 传入希望保存的文件的路径str（必须）、title（可选，用处不大）和author（可选，用处不大）
pdf = PyPDFWriter("report.pdf", "demo pdf to show all features", "LuoChang")

```

## 各项样式介绍

### 添加1-5级标题

支持添加1-5级标题，函数为`pdf.add_heading()`。

参数：

- text（必填），str，标题文本
- level（必填），int，标题级别，可填1-5，若参数非法，小于1则设定为1，大于5则设定为5
- align（可选），str，对齐方式，有3个合法参数：LEFT CENTER RIGHT，默认为LEFT，若参数非法，则会报错

```python
# 标题
pdf.add_heading("一级标题", level=1)
pdf.add_heading("二级居中标题", level=2, align="CENTER")
pdf.add_heading("1.1.1 三级靠右标题（需要自己写序号）", level=3, align="RIGHT")

```

### 添加正文

支持添加正文段落，函数为 `pdf.add_text()`。正文默认使用 `Body_CN` 样式（HarmonyOS Sans，中文自动换行，两端对齐）。正文中的换行符
`\n` 会自动转换为 `<br/>`。

函数签名（核心参数）：

- text（必填），str，正文文本（支持在文本中嵌入简单 XML 标签，例如 `<b>...</b>`、`<font color='...'>...</font>`、
  `<font backColor='...'>...</font>`）
- style（可选），str，样式名，默认 `"Body_CN"`
- align（可选），str，对齐方式，合法参数：`LEFT / CENTER / RIGHT / JUSTIFY`，默认 `LEFT`（不传时沿用样式默认的 `TA_JUSTIFY`）
- color（可选），str，颜色名（会从 `reportlab.lib.colors` 里取同名颜色，如 `grey / red / green` 等；找不到则默认为黑色）

```python
# 1) 基础正文
pdf.add_text("这是默认正文（Body_CN），中文会自动换行，且默认两端对齐。")

# 2) 富文本（XML 标签）
pdf.add_text(
    "支持 <b>加粗</b>，支持 <font color='#d63031'>自定义颜色</font>，"
    "支持 <font backColor='#ffeaa7'>背景高亮</font>。\n"
    "换行用 \\n 即可。"
)

# 3) 指定对齐方式
pdf.add_text("这是两端对齐 JUSTIFY。", align="JUSTIFY")
pdf.add_text("这是居中 CENTER。", align="CENTER")
pdf.add_text("这是右对齐 RIGHT。", align="RIGHT")

# 4) 指定颜色（颜色名来自 reportlab.colors）
pdf.add_text("灰色文字示例", color="grey")
```

示例中的“富文本、对齐、颜色”写法可参考 `main.py` 的演示段落。

### 添加竖向空白

支持添加竖向空白（间距），函数为 `pdf.add_spacer()`。

参数：

- height_mm（可选），int/float，空白高度（单位：mm），默认 `5`

```python
pdf.add_text("上一段")
pdf.add_spacer(10)  # 10mm 空白
pdf.add_text("下一段")
```

### 添加换页符

支持强制换页，函数为 `pdf.add_page_break()`。

```python
pdf.add_heading("第一页内容", level=2)
pdf.add_text("......")

pdf.add_page_break()

pdf.add_heading("第二页内容", level=2)
pdf.add_text("......")
```

### 添加多级有序/无序列表

支持“多级嵌套”列表，函数为 `pdf.add_list()`。

参数：

- items（必填），`List[Union[str, list]]`，列表数据（用“字符串 + 可选子 list”的方式表达层级）
- is_ordered（可选），bool，是否为有序列表，默认 `False`

层级符号规则（库内部已固定）：

- 无序列表：第1层 `•` → 第2层 `◦` → 第3层 `▪`（之后按层级循环）
- 有序列表：第1层 `1.`（数字） → 第2层 `a.`（小写字母） → 第3层 `i.`（罗马数字）（之后按层级循环）

```python
# 1) 无序列表（字符串后面紧跟一个 list 表示其子项）
unordered_data = [
    "项目 A：后端开发",
    [
        "语言：Python",
        [
            "框架：Django",
            "框架：FastAPI"
        ],
        "数据库：PostgreSQL"
    ],
    "项目 B：前端开发",
    [
        "框架：Vue 3",
        "工具：Vite"
    ],
]
pdf.add_list(unordered_data, is_ordered=False)

# 2) 有序列表
ordered_data = [
    "第一阶段：需求分析",
    [
        "收集用户反馈",
        ["问卷调查", "用户访谈"],
        "制定产品文档 (PRD)"
    ],
    "第二阶段：系统设计",
    [
        "数据库设计 (ER图)",
        "接口定义 (OpenAPI)"
    ],
]
pdf.add_list(ordered_data, is_ordered=True)
```

完整深度嵌套测试可参考 `main.py` 的“列表系统”段落。

### 添加代码块

支持添加“可复制文本”的代码块，函数为 `pdf.add_code()`（内部使用 Pygments 做 token 高亮；若环境缺少 Pygments，会降级为无高亮纯文本）。

<p color="red">注意，添加代码块的函数好像还有些bug，不建议添加太长超过一页的代码</p>

参数：

- code_str（必填），str，代码内容
- language（可选），str，语言名（如 `python/json` 等），默认 `python`
- theme（可选），str，主题选择，目前内置有四个主题 `vscode /github / intellij / monokai`，默认`github`，后续期望增加更多的主题

```python
python_code = """class PDFGenerator:
    def __init__(self, filename):
        self.filename = filename

    def build(self):
        # comment
        print(f"Building {self.filename}...")
        return True
"""
pdf.add_code(python_code, language="python", theme="intellij")

json_code = """{
  "project": "PyPDFWriter",
  "version": 2.0,
  "features": ["Syntax Highlighting", "Nested Lists", "Custom Fonts"]
}"""
pdf.add_code(json_code, language="json", theme="vscode")
```

代码块示例可参考 `main.py` 的“代码高亮”段落。

### 添加表格

支持添加表格，函数为 `pdf.add_table()`（支持自动列宽分配；支持表头；单元格内可用简单 XML 标签）。

目前不支持设置表格整体和单元格内文字的对齐方式。

参数：

- data（必填），`List[List[str]]`，二维表格数据
- col_widths（可选），`List[float]`，自定义列宽（不传则自动计算并适配页面宽度）
- has_header（可选），bool，是否有表头（若为 True：第一行加粗、并加浅灰表头背景），默认 `True`

```python
# 1) 标准表格：带表头
table_data = [
    ["模块名称", "负责人", "进度", "状态"],
    ["核心库 (Core)", "张三", "100%", "<font color='green'>已完成</font>"],
    ["UI 组件", "李四", "85%", "<b>测试中</b>"],
    ["文档编写", "王五", "40%", "<font color='red'>延迟</font>"],
]
pdf.add_table(table_data, has_header=True)

# 2) 键值对：无表头（常用于参数清单）
params_data = [
    ["服务器 IP", "192.168.1.100"],
    ["端口", "8080"],
    ["调试模式", "开启"],
]
pdf.add_table(params_data, has_header=False)
```

表格用法可参考 `main.py` 的“数据表格”段落。

### 添加公式块

支持插入 LaTeX 公式（内部用 Matplotlib 渲染为透明 PNG 再插入 PDF）。

参数：

- latex_str（必填），str，LaTeX 公式内容（不要写外层 `$...$`，函数内部会自动包裹）
- fontsize（可选），int/float，字号，默认 `12`

```python
pdf.add_text("下面是正态分布公式：")
pdf.add_formula(r"f(x) = \frac{1}{\sigma\sqrt{2\pi}} e^{-\frac{1}{2}(\frac{x-\mu}{\sigma})^2}")

pdf.add_text("以及爱因斯坦质能方程：")
pdf.add_formula(r"E = mc^2", fontsize=14)
```

公式示例可参考 `main.py` 的“公式”段落。

## 保存

完成内容添加后，调用 `pdf.save()` 输出 PDF。

```python
pdf.save()
```

## 总结与所有代码

如果你想直接跑一个“全功能演示”，可以直接运行 `python main.py`：它把标题、正文（富文本/对齐/颜色）、多级列表、代码块、表格、公式、结尾等功能串成一份完整
PDF。

最小可运行示例（建议先用这个确认环境、字体目录结构都正常）：

```python
from pypdf_writer import PyPDFWriter

pdf = PyPDFWriter("report.pdf", "Demo Report", "LuoChang")

pdf.add_heading("示例报告", level=1, align="CENTER")
pdf.add_text("这是一段正文，支持 <b>加粗</b> 和 <font color='blue'>颜色</font>。")

pdf.add_heading("列表演示", level=2)
pdf.add_list(["第一项", ["子项 1", "子项 2"], "第二项"], is_ordered=False)

pdf.add_heading("代码演示", level=2)
pdf.add_code("print('hello')\n", language="python")

pdf.add_heading("表格演示", level=2)
pdf.add_table([["k", "v"], ["mode", "debug"]], has_header=True)

pdf.add_heading("公式演示", level=2)
pdf.add_formula(r"E = mc^2")

pdf.save()
```

