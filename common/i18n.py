import os
import yaml
from typing import Dict, Optional

class I18n:
    def __init__(self, default_language: str = 'en-US'):
        self.default_language = default_language
        self.current_language = default_language
        self.translations: Dict[str, Dict] = {}
        self._load_translations()
    
    def _load_translations(self):
        """加载所有可用的语言包"""
        i18n_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'i18n')
        for file in os.listdir(i18n_dir):
            if file.endswith('.yaml'):
                language = file.replace('.yaml', '')
                with open(os.path.join(i18n_dir, file), 'r', encoding='utf-8') as f:
                    self.translations[language] = yaml.safe_load(f)
    
    def set_language(self, language: str) -> None:
        """设置当前使用的语言"""
        if language in self.translations:
            self.current_language = language
        else:
            self.current_language = self.default_language
    
    def get_language(self) -> str:
        """获取当前使用的语言"""
        return self.current_language
    
    def get_text(self, key: str, params: Optional[Dict] = None) -> str:
        """获取翻译文本，支持参数插值
        
        Args:
            key: 翻译键值，使用点号分隔，如 'common.success'
            params: 插值参数字典，如 {'field': 'username'}
        
        Returns:
            翻译后的文本
        """
        # 获取当前语言的翻译
        translations = self.translations.get(self.current_language, {})
        if not translations:
            translations = self.translations.get(self.default_language, {})
        
        # 按照点号分隔键值查找翻译
        text = translations
        for part in key.split('.'):
            if isinstance(text, dict) and part in text:
                text = text[part]
            else:
                return key  # 如果找不到翻译，返回原始键值
        
        # 如果不是字符串类型，返回原始键值
        if not isinstance(text, str):
            return key
        
        # 执行参数插值
        if params:
            try:
                text = text.format(**params)
            except KeyError:
                pass
        
        return text

# 创建全局实例
i18n = I18n()