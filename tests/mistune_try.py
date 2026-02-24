from pprint import pprint

import mistune


# --- 核心可视化代码 (直接追加) ---

def dump_ast_tree(node, prefix="", is_last=True):
    """
    递归打印 mistune AST 树结构
    """
    # 树枝符号处理
    connector = "└── " if is_last else "├── "

    # 根节点通常是列表，直接遍历
    if isinstance(node, list):
        for i, child in enumerate(node):
            dump_ast_tree(child, prefix, is_last=(i == len(node) - 1))
        return

    # 提取关键信息
    node_type = node.get('type', 'unknown')
    # 提取内容摘要 (text, src, 或 params)，避免打印过多噪点
    info = []
    if 'raw' in node: info.append(f"raw: {node['raw'][:100]}{'...' if len(node['raw']) > 100 else ''}")  # 截断长文本
    if 'attrs' in node: info.append(f"attr: {node['attrs']}")

    content_str = f" | {', '.join(info)}" if info else ""

    # 打印当前节点
    print(f"{prefix}{connector}\033[1;36m{node_type}\033[0m{content_str}")

    # 处理子节点 (children)
    if 'children' in node:
        children = node['children']
        new_prefix = prefix + ("    " if is_last else "│   ")
        for i, child in enumerate(children):
            dump_ast_tree(child, new_prefix, is_last=(i == len(children) - 1))


with open("DeepSeekV3_2.md", "r", encoding="utf-8") as f:
    text = f.read()
    f.close()

markdown = mistune.create_markdown(
    renderer=None,  # 做解析，不是渲染
    plugins=[
        'speedup',
        'strikethrough',
        'mark',
        'insert',
        'superscript',
        'subscript',
        'footnotes',
        'table',
        'url',
        'abbr',
        'def_list',
        'math',
        'ruby',
        'task_lists',
        'spoiler'
    ]
)
ast = markdown(text)
pprint(ast)
# --- 执行 ---
print("\nAST Structure:")
dump_ast_tree(ast)
