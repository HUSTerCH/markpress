import time
import sys
import traceback
from pathlib import Path

# 确保导入了你的批量处理函数
from markpress.converter import convert_markdown_batch

DATASET_DIR = Path("/Users/luochang/.cache/modelscope/hub/datasets/OpenDataLab/awesome-markdown-ebooks/ChinaTextbook")
EXPORT_DIR = Path("/Users/luochang/.cache/modelscope/hub/datasets/OpenDataLab/awesome-markdown-ebooks/ChinaTextbook_PDF")

# 1. 扫描文件
markdown_files = sorted(DATASET_DIR.rglob("*.md"))

tasks = []
for md_file in markdown_files:
    # 【修复1：保留相对路径层级，防止同名覆盖】
    # 比如 src/Math/ch1.md -> EXPORT_DIR/Math/ch1.pdf
    relative_path = md_file.relative_to(DATASET_DIR)
    pdf_path = EXPORT_DIR / relative_path.with_suffix(".pdf")

    # 【修复2：断点续传检查】
    # 如果 PDF 已经存在且大小不为 0，说明上次成功了，直接跳过
    if pdf_path.exists() and pdf_path.stat().st_size > 0:
        continue

    # 确保输出子目录存在
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    tasks.append((str(md_file), str(pdf_path)))

print(f"总扫描到 {len(markdown_files)} 个文件。")
print(f"排除已完成项后，剩余待处理任务: {len(tasks)} 个。")
with open("error-files-20260306.txt", "w",encoding='utf-8') as f:
    for task in tasks:
        f.write(task[0] + "\n")
exit(0)

# 如果没有任务，直接退出
if not tasks:
    print("所有文件均已转换完毕！")
    sys.exit(0)

# 2. 核心调度：分批执行策略
BATCH_SIZE = 50  # 每批处理 50 个文件，防止内存泄漏或 Chromium 卡死

for i in range(0, len(tasks), BATCH_SIZE):
    batch = tasks[i:i + BATCH_SIZE]
    current_batch_num = i // BATCH_SIZE + 1
    total_batches = (len(tasks) + BATCH_SIZE - 1) // BATCH_SIZE

    print(f"\n" + "=" * 50)
    print(f"🚀 开始执行第 {current_batch_num}/{total_batches} 批次 (文件 {i + 1} - {min(i + BATCH_SIZE, len(tasks))})")
    print(f"=" * 50)

    start_time = time.time()

    try:
        # 调用你的批量管线
        if "/Users/luochang/.cache/modelscope/hub/datasets/OpenDataLab/awesome-markdown-ebooks/ChinaTextbook/大学/概率论/概率论与数理统计(浙大四版)/vlm/概率论与数理统计(浙大四版).md" not in batch[0]:
            convert_markdown_batch(batch, theme="vue")
    except Exception as e:
        # 【系统级防爆破】：只有极其致命的错误才会漏到这里
        print(f"\n[FATAL ERROR] 💀 第 {current_batch_num} 批次发生系统级崩溃！")

        with open("error.log", "a", encoding="utf-8") as log_file:
            log_file.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] === 批次 {current_batch_num} 系统级致命崩溃 ===\n")
            traceback.print_exc(file=log_file)
            log_file.write("\n\n" + "=" * 80 + "\n\n")

        print("已记录系统级错误，准备重置环境并执行下一批...")

    elapsed = time.time() - start_time
    print(f"\n✅ 批次 {current_batch_num} 结束。耗时: {elapsed:.2f} 秒")

    # 强制让系统休息 5 秒，释放文件句柄和网络 I/O
    time.sleep(5)

print("\n🎉 全部分批测试任务执行完毕。")