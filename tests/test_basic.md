# MarkPress 核心功能测试
当前支持：
1. 代码块，已经修复代码块过大报错的问题
2. 正文富文本（持续测试中），暂不支持列表
## 1. 文本排版 (Typography)

这是标准正文文本。MarkPress 应该能够完美渲染**加粗文字 (Bold)**、*斜体文字 (Italic)*、***加粗和斜体(Bold and Italic)***。

> 这是单层嵌套这是单层嵌套这是单层嵌套这是单层嵌套这是单层嵌套这是单层嵌套这是单层嵌套这是单层嵌套这是单层嵌套这是单层嵌套这是单层嵌套这是单层嵌套这是单层嵌套这是单层嵌套这是单层嵌套

> 这是一段引用文本和这是一段引用文本和这是一段引用文本和这是一段引用文本和这是一段引用文本和这是一段引用文本和这是一段引用文本和
> > 嵌套引用文本嵌套引用文本嵌套引用文本嵌套引用文本嵌套引用文本嵌套引用文本嵌套引用文本嵌套引用文本
> > > 多级嵌套引用文本

同时也需要测试 中文长段落的自动换行 和 两端对齐 (Justify) 功能。如果这段文字足够长，它应该在PDF的右侧边界处整齐折行，而不是直接溢出页面或者留下难看的锯齿状边缘。工业级的排版要求中英文混排时（如 Python 与 C++）也能保持基线对齐。
这样的对齐方式才是看的赏心悦目的

再来试试font设置<font color="red">红色字体</font>和span设置<span style="background: yellow">黄色背景</span>

再来试试多级列表：

1. 一级列表结合行内公式$\frac{\partial \mathbf{u}}{\partial t} + (\mathbf{u} \cdot \nabla) \mathbf{u} = -\frac{1}{\rho} \nabla p + \nu \nabla^2 \mathbf{u} + \mathbf{g}$
2. 一级列表**加粗**
3. 一级列表*斜体*
   1. 二级列表***加粗斜体***
   2. 二级列表
   3. 二级列表
      1. 三级列表
      2. 三级列表
      3. 三级列表
         1. 四级列表

> - 嵌套的列表
> - 嵌套的列表
>   - 嵌套的二级列表
> 
> 1. 嵌套的一级列表
> 2. 嵌套的一级列表
>    1. 嵌套的二级列表

- 一级无序
- 一级无序
- 一级无序
  - 二级无序
  - 二级无序
  - 二级无序
    - 三级无序
    - 三级无序
      - 四级无序

# MarkPress 公式压力测试

## 1. 极限行内混排 (Inline Alignment)
我们从最基础的 $E=mc^2$ 开始，然后迅速进入复杂模式。
在量子场论中，路径积分的形式 $Z = \int \mathcal{D}\phi \, e^{i \int d^4x \mathcal{L}}$ 是核心。
即使是简单的泰勒展开 $f(x) = \sum_{n=0}^{\infty} \frac{f^{(n)}(a)}{n!} (x-a)^n$ 也能测试分数的垂直对齐。
如果你的渲染器不够强，这个嵌入的矩阵$\begin{bmatrix} \frac{1}{3}&\frac{2}{3}&0\\ \frac{2}{9}&\frac{5}{9}&\frac{2}{9}\\ 0&\frac{1}{3}&\frac{2}{3}\\ \end{bmatrix}$可能会把行高撑爆，或者基线乱飞。
再来试试超长的公式，希望不要再被撑爆了：$3 = \sqrt{1 + 2\sqrt{1 + 3\sqrt{1 + 4\sqrt{1 + 5\sqrt{1 + \cdots}}}}}$

## 2. 纳维-斯托克斯方程 (Navier-Stokes)
流体力学核心方程，测试 **矢量算符 ($\nabla$)**、**偏微分** 和 **长公式缩放**：
$$
\frac{\partial \mathbf{u}}{\partial t} + (\mathbf{u} \cdot \nabla) \mathbf{u} = -\frac{1}{\rho} \nabla p + \nu \nabla^2 \mathbf{u} + \mathbf{g}
$$

这是行间公式，验证矩阵是否可以转换：

$$
\begin{bmatrix}
\frac{1}{3}&\frac{2}{3}&0\\
\frac{2}{9}&\frac{5}{9}&\frac{2}{9}\\
0&\frac{1}{3}&\frac{2}{3}\\
\end{bmatrix}
$$

## 3. 拉马努金无穷根式 (Nested Radicals)
这是对 **垂直高度计算** 和 **嵌套渲染** 的终极考验。如果图片裁剪（bbox_tight）有问题，最外层的根号会被切掉：
$$
3 = \sqrt{1 + 2\sqrt{1 + 3\sqrt{1 + 4\sqrt{1 + 5\sqrt{1 + \cdots}}}}}
$$

## 4. 广义相对论场方程 (General Relativity)
测试 **张量下标**、**希腊字母** 和 **分式组合**：
$$
R_{\mu\nu} - \frac{1}{2}R g_{\mu\nu} + \Lambda g_{\mu\nu} = \frac{8\pi G}{c^4} T_{\mu\nu}
$$

## 5. 柯西积分公式 (Cauchy Integral Formula)
测试 **闭合围道积分** 和 **大括号**：
$$
f^{(n)}(a) = \frac{n!}{2\pi i} \oint_{\gamma} \frac{f(z)}{(z-a)^{n+1}} \, dz
$$

## 6. 标准模型拉格朗日量 (Standard Model - The Beast)
测试 **超高密度符号**。如果渲染出来糊成一团，说明 DPI 不够；如果溢出页面，说明自动缩放失效：
$$
\mathcal{L} = -\frac{1}{4} F_{\mu\nu} F^{\mu\nu} + i \bar{\psi} \not D \psi + h.c. + \psi_i y_{ij} \psi_j \phi + h.c. + |D_\mu \phi|^2 - V(\phi)
$$


<font size=20 color="green">行间html</font>


这是一个链接 *[Markdown语法](https://markdown.com.cn)*。

还可以这么写：<https://markdown.com.cn>

电子邮件：<fake@example.com>

分割线

---

### 1.1 字体测试 (Font Fallback)

Testing English font mixed with 中文显示. 1234567890 (Numbers).

## 2. 代码块 (Code Snippets)

下面是一段 Python 代码，用于测试`CodeRenderer`的背景色、边框以及`JetBrainsMono`字体渲染：

```python
import mistune
from .core import MarkPressEngine


def convert_markdown_file(input_path: str, output_path: str, theme: str = "academic"):
    # 1. 读取文件
    with open(input_path, "r", encoding="utf-8") as f:
        text = f.read()
    # 初始化 Mistune
    markdown = mistune.create_markdown(
        renderer=None,  # 做解析，不是渲染
        plugins=['speedup','strikethrough','mark','insert','superscript','subscript','footnotes','table','url',
            'abbr',
            'def_list',
            'math',
            'ruby',
            'task_lists',
            'spoiler'
        ]
    )
    # 3. 获取 AST (Abstract Syntax Tree)
    # 这是一个由字典组成的列表，每个字典代表一个 Block (段落, 标题, 代码块等)
    ast = markdown(text)
    # 4. 初始化 PDF 引擎
    writer = MarkPressEngine(output_path, theme)

    # 5. 遍历 AST 并渲染
    _render_ast(writer, ast)

    # 6. 保存
    writer.save()
```

## 3. 样式层级 (Hierarchy)

### 三级标题 (H3)

正文内容...

正文内容...

正文内容...

正文内容...

正文内容...

### 三级标题
#### 四级标题 (H4)

这里测试紧凑的小标题样式。

```json
{
    "theme": "academic",
    "debug": true,
    "supported_formats": [
        "md",
        "rst"
    ]
}
```