import time
import sys
import traceback
from pathlib import Path

# 确保导入了你的批量处理函数
from markpress.converter import convert_markdown_batch

DATASET_DIR = Path("/Users/zq/.cache/modelscope/hub/datasets/OpenDataLab/awesome-markdown-ebooks/ChinaTextbook")
EXPORT_DIR = Path("/Users/zq/.cache/modelscope/hub/datasets/OpenDataLab/awesome-markdown-ebooks/ChinaTextbook_PDF")
ERROR_FILES_LIST = Path(__file__).parent / "error-files-20260309.txt"
LOG_DIR = Path(__file__).parent / "logs"
RUN_STAMP = time.strftime("%Y%m%d-%H%M%S")
RUN_TIME = time.strftime("%Y-%m-%d %H:%M:%S")

FAILED_FILES_OUTPUT = LOG_DIR / f"failed-files-{RUN_STAMP}.txt"
ERROR_LOG_OUTPUT = LOG_DIR / f"error-{RUN_STAMP}.log"
REPORT_OUTPUT = LOG_DIR / f"report-{RUN_STAMP}.md"


def write_file(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

# 1. 从上次报错样本列表读取待重跑文件
LOG_DIR.mkdir(parents=True, exist_ok=True)
tasks = []
with open(ERROR_FILES_LIST, encoding="utf-8") as f:
    for line in f:
        md_path_str = line.strip()
        if not md_path_str:
            continue
        md_file = Path(md_path_str)
        if not md_file.exists():
            print(f"[跳过] 文件不存在: {md_path_str}")
            continue
        # 保留相对路径层级，防止同名覆盖
        try:
            relative_path = md_file.relative_to(DATASET_DIR)
        except ValueError:
            print(f"[跳过] 路径不在 DATASET_DIR 下: {md_path_str}")
            continue
        pdf_path = EXPORT_DIR / relative_path.with_suffix(".pdf")
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        tasks.append((str(md_file), str(pdf_path)))

print(f"从 {ERROR_FILES_LIST.name} 加载 {len(tasks)} 个待重跑样本。")
print(f"日志输出目录: {LOG_DIR}")

# 如果没有任务，直接退出
if not tasks:
    print("所有文件均已转换完毕！")
    empty_report = "\n".join([
        f"# Batch Test Report - {RUN_STAMP}",
        f"生成时间: {RUN_TIME}",
        f"输入文件列表: {ERROR_FILES_LIST.name}",
        "待测文件数: 0",
        "说明: 没有可执行任务。",
    ])
    write_file(REPORT_OUTPUT, empty_report + "\n")
    sys.exit(0)

# 2. 核心调度：分批执行策略
BATCH_SIZE = 50  # 每批处理 50 个文件，防止内存泄漏或 Chromium 卡死
total_batches = (len(tasks) + BATCH_SIZE - 1) // BATCH_SIZE

write_file(
    ERROR_LOG_OUTPUT,
    "\n".join([
        f"[{RUN_TIME}] Batch 测试错误日志",
        f"输入文件列表: {ERROR_FILES_LIST.name}",
        f"待测文件总数: {len(tasks)}",
        "",
    ]) + "\n",
)

run_start = time.time()
overall_failures = []
batch_summaries = []
fatal_batches = []

for i in range(0, len(tasks), BATCH_SIZE):
    batch = tasks[i:i + BATCH_SIZE]
    current_batch_num = i // BATCH_SIZE + 1

    print(f"\n" + "=" * 50)
    print(f"🚀 开始执行第 {current_batch_num}/{total_batches} 批次 (文件 {i + 1} - {min(i + BATCH_SIZE, len(tasks))})")
    print(f"=" * 50)

    start_time = time.time()

    try:
        # 调用批量管线
        batch_result = convert_markdown_batch(
            batch,
            theme="vue",
            error_log_path=str(ERROR_LOG_OUTPUT),
        )
        overall_failures.extend(batch_result["failures"])
    except Exception as e:
        # 【系统级防爆破】：只有极其致命的错误才会漏到这里
        print(f"\n[FATAL ERROR] 💀 第 {current_batch_num} 批次发生系统级崩溃！")
        fatal_time = time.strftime('%Y-%m-%d %H:%M:%S')
        fatal_batches.append({
            "batch": current_batch_num,
            "timestamp": fatal_time,
            "error_type": type(e).__name__,
            "error_message": str(e),
        })

        with open(ERROR_LOG_OUTPUT, "a", encoding="utf-8") as log_file:
            log_file.write(f"[{fatal_time}] === 批次 {current_batch_num} 系统级致命崩溃 ===\n")
            traceback.print_exc(file=log_file)
            log_file.write("\n\n" + "=" * 80 + "\n\n")

        print("已记录系统级错误，准备重置环境并执行下一批...")
        overall_failures.extend([
            {
                "timestamp": fatal_time,
                "input_path": input_path,
                "output_path": output_path,
                "error_type": type(e).__name__,
                "error_message": f"批次级致命崩溃: {e}",
            }
            for input_path, output_path in batch
        ])
        batch_result = {
            "total": len(batch),
            "succeeded": 0,
            "failed": len(batch),
            "failures": [],
        }

    elapsed = time.time() - start_time
    batch_summaries.append({
        "batch": current_batch_num,
        "size": len(batch),
        "succeeded": batch_result["succeeded"],
        "failed": batch_result["failed"],
        "elapsed_seconds": elapsed,
    })
    print(f"\n✅ 批次 {current_batch_num} 结束。耗时: {elapsed:.2f} 秒")

    # 强制让系统休息 5 秒，释放文件句柄和网络 I/O
    time.sleep(5)

print("\n🎉 全部分批测试任务执行完毕。")

failed_file_lines = [
    f"# Failed Files - {RUN_STAMP}",
    f"生成时间: {RUN_TIME}",
    f"输入文件列表: {ERROR_FILES_LIST.name}",
    f"失败文件数: {len(overall_failures)}",
    "",
]
failed_file_lines.extend(item["input_path"] for item in overall_failures)
write_file(FAILED_FILES_OUTPUT, "\n".join(failed_file_lines) + "\n")

total_elapsed = time.time() - run_start
total_success = sum(item["succeeded"] for item in batch_summaries)
total_failed = sum(item["failed"] for item in batch_summaries)

report_lines = [
    f"# Batch Test Report - {RUN_STAMP}",
    f"生成时间: {RUN_TIME}",
    f"输入文件列表: {ERROR_FILES_LIST.name}",
    f"待测文件总数: {len(tasks)}",
    f"批次数: {total_batches}",
    f"成功数: {total_success}",
    f"失败数: {total_failed}",
    f"系统级崩溃批次: {len(fatal_batches)}",
    f"总耗时(秒): {total_elapsed:.2f}",
    "",
    "## 输出文件",
    f"- 错误详情日志: {ERROR_LOG_OUTPUT.name}",
    f"- 失败文件清单: {FAILED_FILES_OUTPUT.name}",
    f"- 汇总报告: {REPORT_OUTPUT.name}",
    "",
    "## 批次统计",
]

for batch_item in batch_summaries:
    report_lines.append(
        f"- 第 {batch_item['batch']}/{total_batches} 批: "
        f"总数 {batch_item['size']}，成功 {batch_item['succeeded']}，失败 {batch_item['failed']}，"
        f"耗时 {batch_item['elapsed_seconds']:.2f} 秒"
    )

report_lines.extend(["", "## 失败文件"])
if overall_failures:
    for failure in overall_failures:
        report_lines.append(
            f"- [{failure['timestamp']}] {failure['input_path']} | "
            f"{failure['error_type']}: {failure['error_message']}"
        )
else:
    report_lines.append("- 无")

report_lines.extend(["", "## 系统级崩溃批次"])
if fatal_batches:
    for fatal in fatal_batches:
        report_lines.append(
            f"- [{fatal['timestamp']}] 第 {fatal['batch']} 批 | "
            f"{fatal['error_type']}: {fatal['error_message']}"
        )
else:
    report_lines.append("- 无")

write_file(REPORT_OUTPUT, "\n".join(report_lines) + "\n")

print("\n📁 日志文件已生成:")
print(f"- 错误详情日志: {ERROR_LOG_OUTPUT}")
print(f"- 失败文件清单: {FAILED_FILES_OUTPUT}")
print(f"- 汇总报告: {REPORT_OUTPUT}")
