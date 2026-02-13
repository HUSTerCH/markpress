from pypdf_writer import PyPDFWriter


def generate_full_demo():
    # 0. 初始化
    OUTPUT_FILE = r"demo_full_features.pdf"

    print(f"正在生成: {OUTPUT_FILE} ...")
    pdf = PyPDFWriter(OUTPUT_FILE, "demo pdf to show all features", "LuoChang")

    # 封面 / 顶部信息，其实也是标题和正文的样式
    pdf.add_heading("PyPDFWriter 全功能演示", level=1, align="CENTER")
    pdf.add_text("生成时间：2026-01-21", align="CENTER", color="grey")
    pdf.add_text("--- 演示开始 ---", align="CENTER", color="grey")

    # 1. 标题层级展示 (H1 - H5)
    pdf.add_heading("1. 标题层级演示", level=1)
    pdf.add_text("以下展示 H2 到 H5 的标题样式与间距：")

    pdf.add_heading("1.1 二级标题 (H2)", level=2)
    pdf.add_heading("1.1.1 三级标题 (H3)", level=3, align="RIGHT")
    pdf.add_heading("1.1.1.1 四级标题 (H4)", level=4)
    pdf.add_heading("1.1.1.1.1 五级标题 (H5)", level=5)

    pdf.add_page_break()

    # 2. 正文与富文本样式
    pdf.add_heading("2. 正文排版与样式", level=1)

    # 基础样式
    pdf.add_heading("2.1 富文本支持", level=2)
    pdf.add_text(
        "PyPDFWriter 支持在正文中直接嵌入 XML 标签来实现样式控制。例如：\n"
        "可以设置 <b>加粗字体 (Bold)</b> 以强调重点。\n"
        "可以设置 <i>斜体 (Italic)</i> 以突出显示。\n"
        "可以同时设置<b><i>加粗斜体 (Bold and Italic) </i></b>以更加强调显示。\n"
        "可以设置 <font color='#d63031'>自定义文字颜色 (Red)</font> 或 <font color='blue'>蓝色 (Blue)</font>。\n"
        "也可以设置 <font backColor='#ffeaa7'>背景高亮颜色 (Highlight)</font> 用于标记。"
    )

    # 对齐方式
    pdf.add_heading("2.2 对齐方式", level=2)
    pdf.add_text("这是默认的左对齐/两端对齐 (JUSTIFY) 文本。HarmonyOS Sans 阅读体验良好。", align="JUSTIFY")
    pdf.add_text("这是居中对齐 (CENTER) 的文本。", align="CENTER")
    pdf.add_text("这是右对齐 (RIGHT) 的文本。", align="RIGHT")

    pdf.add_page_break()
    # 3. 列表系统 (核心修复项)
    pdf.add_heading("3. 列表系统 (深度嵌套测试)", level=1)

    # 无序列表测试
    pdf.add_heading("3.1 无序列表 (Unordered List)", level=2)
    pdf.add_text("测试目标：一级实心圆-> 二级空心圆-> 三级实心方块。")

    unordered_data = [
        "项目 A：后端开发",
        [
            "语言：Python",
            [
                "框架：Django",
                "框架：FastAPI (高性能)"
            ],
            "语言：Golang",
            "数据库：PostgreSQL"
        ],
        "项目 B：前端开发",
        [
            "框架：Vue 3",
            "工具：Vite"
        ],
        "项目 C：部署运维"
    ]
    pdf.add_list(unordered_data, is_ordered=False)

    # 有序列表测试
    pdf.add_heading("3.2 有序列表 (Ordered List)", level=2)
    pdf.add_text("测试目标：一级数字(1.) -> 二级字母(a.) -> 三级罗马数字(i.)，且数字后强制带点。")

    ordered_data = [
        "第一阶段：需求分析",
        [
            "收集用户反馈",
            [
                "问卷调查",
                "用户访谈",
                "问卷调查",
                "用户访谈"
            ],
            "制定产品文档 (PRD)"
        ],
        "第二阶段：系统设计",
        [
            "数据库设计 (ER图)",
            "接口定义 (OpenAPI)"
        ],
        "第三阶段：开发与测试"
    ]
    pdf.add_list(ordered_data, is_ordered=True)
    pdf.add_page_break()

    # 4. 代码
    pdf.add_heading("4. 代码块", level=1)

    # Python 示例
    pdf.add_heading("4.1 Python 示例", level=3)
    python_code = """class PDFGenerator:
    def __init__(self, filename):
        self.filename = filename
    
    def build(self):
        # 这是一个注释
        print(f"Building {self.filename}...")
        return True"""
    pdf.add_code(python_code, language="python", theme="intellij")

    # JSON 示例
    pdf.add_heading("4.2 JSON 数据结构", level=3)
    json_code = """{
  "project": "PyPDFWriter",
  "version": 2.0,
  "features": [
    "Syntax Highlighting",
    "Nested Lists",
    "Custom Fonts"
  ]
}"""
    pdf.add_code(json_code, language="json", theme="vscode")
    pdf.add_page_break()

    # 5. 表格展示
    pdf.add_heading("5. 数据表格", level=1)
    pdf.add_text("表格使用 Table 组件，支持自定义列宽和简单的表头样式。")

    table_data = [
        ["模块名称", "负责人", "进度", "状态"],  # 表头
        ["核心库 (Core)", "张三", "100%", "<font color='green'>已完成</font>"],
        ["UI 组件", "李四", "85%", "<b>测试中</b>\n进展顺利"],
        ["文档编写", "王五", "40%", "<font color='red'>延迟</font>"],
        ["部署脚本", "赵六", "100%", "已完成"],
    ]

    # 场景 1：标准数据表格（带表头，自动宽度）
    data_header = [
        ["姓名", "职位", "邮箱"],
        ["张三", "开发工程师", "zhangsan@example.com"],
        ["李四", "产品经理", "lisi@example.com"]
    ]
    pdf.add_table(table_data, has_header=True)

    # 场景 2：键值对/参数列表（无表头，自动宽度）
    data_params = [
        ["服务器 IP", "192.168.1.100"],
        ["端口", "8080"],
        ["调试模式", "开启"]
    ]
    pdf.add_table(data_params, has_header=False)

    # 场景 3：自定义宽度（依然会自动居中）
    pdf.add_table(data_header, has_header=True)
    pdf.add_page_break()

    # 6. 公式
    pdf.add_heading("6. LaTeX 公式 (Matplotlib)", level=2)
    pdf.add_text("下面是正态分布公式：")
    # 注意：字符串前的 r 表示 raw string，避免转义
    pdf.add_formula(r"f(x) = \frac{1}{\sigma\sqrt{2\pi}} e^{-\frac{1}{2}(\frac{x-\mu}{\sigma})^2}")
    pdf.add_text("以及爱因斯坦质能方程：")
    pdf.add_formula(r"E = mc^2")

    # 7. 结束
    pdf.add_spacer(10)
    pdf.add_text("--- 演示结束 ---", align="CENTER", color="grey")

    # 保存
    pdf.save()


if __name__ == "__main__":
    generate_full_demo()
