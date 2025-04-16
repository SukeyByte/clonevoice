import os
import yaml
from typing import Dict, Any
from pathlib import Path

class Config:
    _instance = None
    _config = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        config_dir = Path(__file__).parent.parent / 'config'
        base_config_path = config_dir / 'base.yaml'

        if not base_config_path.exists():
            raise FileNotFoundError(f"基础配置文件不存在: {base_config_path}")

        with open(base_config_path, 'r', encoding='utf-8') as f:
            self._config = yaml.safe_load(f)

    def get_database_config(self) -> Dict[str, Any]:
        return self._config.get('database', {})

    def get_redis_config(self) -> Dict[str, Any]:
        return self._config.get('redis', {})

    def get_rabbitmq_config(self) -> Dict[str, Any]:
        return self._config.get('rabbitmq', {})

    def get_logging_config(self) -> Dict[str, Any]:
        return self._config.get('logging', {})

    @property
    def config(self) -> Dict[str, Any]:
        return self._config

# 创建全局配置实例
config = Config()