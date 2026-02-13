from abc import ABC, abstractmethod
from typing import List, Any
from reportlab.platypus import Flowable
from reportlab.lib.styles import StyleSheet1
from ..themes import StyleConfig

class BaseRenderer(ABC):
    """
    所有渲染器的基类。
    必须持有 style_config 用于获取颜色/字体配置。
    必须持有 stylesheet 用于获取 ReportLab 的 ParagraphStyle。
    """
    def __init__(self, config: StyleConfig, stylesheet: StyleSheet1):
        self.config = config
        self.styles = stylesheet

    @abstractmethod
    def render(self, data: Any, **kwargs) -> List[Flowable]:
        """
        核心方法：将数据转换为 ReportLab 的 Flowable 列表。
        :param data: 具体的数据 (str, dict, list 等)
        :return: [Flowable, ...] (返回列表是因为一个组件可能生成多个元素，如代码块+标题)
        """
        pass