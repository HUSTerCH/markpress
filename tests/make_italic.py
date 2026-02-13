# make_italic.py
import fontforge
import psMat
import math

# 配置
INPUT_FILE = "/markpress/assets/fonts/ms-yahei-bold.ttf"
OUTPUT_FILE = "/markpress/assets/fonts/ms-yahei-bold-italic.ttf"
SKEW_ANGLE_DEG = 12  # 标准倾斜角度


def main():
    print(f"[-] Loading {INPUT_FILE}...")
    try:
        font = fontforge.open(INPUT_FILE)
    except Exception as e:
        print(f"[!] Error opening file: {e}")
        return

    # 1. 修改元数据 (Metadata)
    # 必须修改，否则系统会认为它还是 Regular，安装后会冲突
    font.fontname = font.fontname + "Italic"
    font.fullname = font.fullname + " Italic"
    font.familyname = font.familyname  # 家族名通常保持不变或加后缀，视需求而定
    font.italicangle = -SKEW_ANGLE_DEG  # 注意：FontForge中负值表示向右倾斜
    font.weight = "Bold"  # 或保持 Regular

    # 2. 几何变换 (Geometric Transformation)
    print(f"[-] Skewing glyphs by {SKEW_ANGLE_DEG} degrees...")

    # 计算弧度
    # psMat.skew(radians)
    # 这里的 skew 转换矩阵大致为 [1, 0, tan(angle), 1, 0, 0]
    # 注意：FontForge 的 skew 行为可能需要根据版本微调，通常正弧度向右倾斜
    radians = math.radians(SKEW_ANGLE_DEG)
    skew_matrix = psMat.skew(radians)

    # 选中所有字符
    font.selection.all()
    # 应用变换
    font.transform(skew_matrix)

    # 3. 修正变换后的问题
    # 变换后，字形的极值点（Extrema）会变，需要重新添加以保证渲染质量
    print("[-] Adding extrema (this takes time for CJK)...")
    font.addExtrema()

    # 4. 生成文件
    print(f"[-] Generating {OUTPUT_FILE}...")
    font.generate(OUTPUT_FILE)
    print("[+] Done.")


if __name__ == "__main__":
    main()