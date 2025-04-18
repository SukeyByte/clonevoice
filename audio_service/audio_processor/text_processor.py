import re

class TextProcessor:
    @staticmethod
    def split_text(text: str) -> list:
        return [text]
        """将文本按标点符号分段"""
        # 使用标点符号分割文本
        segments = re.split('[，。！？,.!?]', text)
        # 过滤空字符串并添加标点
        return [seg.strip() for seg in segments if seg.strip()]

    @staticmethod
    def validate_text(text: str) -> bool:
        """验证文本是否有效"""
        if not text or not text.strip():
            return False
        return True