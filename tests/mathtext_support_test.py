"""
test_mathtext_support.py

批量验证 matplotlib mathtext 支持哪些 LaTeX 表达式
运行：
    python test_mathtext_support.py
"""

import os
import traceback
import matplotlib.pyplot as plt

# =========================
# 你要测试的 LaTeX 表达式
# =========================
TEST_FORMULAS = {
    "simple": r"E=mc^2",
    "fraction": r"\frac{a}{b}",
    "sqrt": r"\sqrt{x+1}",
    "nested_sqrt": r"\sqrt{1+2\sqrt{1+3\sqrt{1+4\sqrt{1+5}}}}",
    "sum": r"\sum_{n=0}^{\infty} x^n",
    "integral": r"\int_0^1 x^2 dx",
    "limit": r"\lim_{x\to 0} \frac{\sin x}{x}",
    "greek": r"\alpha + \beta + \gamma",
    "matrix_pmatrix": r"\begin{pmatrix}1&2\\3&4\end{pmatrix}",
    "matrix_bmatrix": r"\begin{bmatrix}1&2\\3&4\end{bmatrix}",
    "matrix_plain": r"\begin{matrix}1&2\\3&4\end{matrix}",
    "cases": r"f(x)=\begin{cases}x^2 & x>0\\0 & x\le 0\end{cases}",
    "align": r"\begin{aligned}a&=b+c\\d&=e+f\end{aligned}",
    "text": r"\text{hello world}",
    "bold": r"\mathbf{A}",
    "overbrace": r"\overbrace{a+b+c}^{sum}",
    "underbrace": r"\underbrace{a+b+c}_{sum}",
}


OUTPUT_DIR = "mathtext_test_output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 使用 STIX 字体更接近 LaTeX
plt.rc("mathtext", fontset="stix")


def formula_test(name, latex):
    """尝试渲染一个公式"""
    try:
        fig = plt.figure(figsize=(2, 1))
        fig.text(0, 0.5, f"${latex}$", fontsize=20)

        path = os.path.join(OUTPUT_DIR, f"{name}.png")
        plt.axis("off")
        plt.savefig(path, bbox_inches="tight", pad_inches=0.1, dpi=200)
        plt.close(fig)

        return True, None

    except Exception as e:
        plt.close("all")
        return False, str(e)


def main():
    supported = []
    failed = []

    print("Testing matplotlib mathtext support...\n")

    for name, latex in TEST_FORMULAS.items():
        ok, err = formula_test(name, latex)

        if ok:
            print(f"[OK]   {name}")
            supported.append(name)
        else:
            print(f"[FAIL] {name}")
            print("       ", err.split("\n")[0])
            failed.append((name, err))

    print("\n==============================")
    print("SUPPORTED:")
    for x in supported:
        print("  ", x)

    print("\nNOT SUPPORTED:")
    for name, err in failed:
        print("  ", name)

    print("\nImages saved to:", OUTPUT_DIR)


if __name__ == "__main__":
    main()
