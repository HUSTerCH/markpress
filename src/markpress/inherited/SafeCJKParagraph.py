from reportlab.platypus import Paragraph


class SafeCJKParagraph(Paragraph):
    """
    一个打了补丁的 Paragraph，用于捕获 ReportLab cjkFragSplit 中的 ord() 错误。
    当检测到 CJK 换行算法崩溃时，它会降级处理，避免程序退出。
    """

    def breakLinesCJK(self, width):
        try:
            # 尝试调用原始的 CJK 换行逻辑
            return super().breakLinesCJK(width)
        except TypeError as e:
            # 捕获经典错误: ord() expected a character, but string of length 0 found
            if "ord() expected a character" in str(e):
                # print(f"Warning: CJK Linebreak crash detected in paragraph. Fallback to standard breaking.")

                # 出现错误时，临时关闭 CJK 换行策略
                # 这会避免 ord() 检查，虽然中文右侧可能不整齐，但能保证 PDF 生成成功
                original_wrap = self.style.wordWrap
                self.style.wordWrap = None

                # 使用标准英语换行算法重试
                result = self.breakLines(width)

                # 恢复设置 (虽然对当前段落没用了，但保持状态一致)
                self.style.wordWrap = original_wrap
                return result
            raise e