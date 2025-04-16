from loguru import logger
from dotenv import load_dotenv
import os
import sys
from datetime import datetime

# 加载环境变量
load_dotenv()

# 日志配置
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_DIR = os.getenv("LOG_DIR", "logs")

# 确保日志目录存在
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

def setup_logger(service_name: str) -> None:
    """配置日志记录器

    Args:
        service_name: 服务名称，用于区分不同服务的日志文件
    """
    # 生成日志文件路径
    log_file = os.path.join(
        LOG_DIR,
        f"{service_name}_{datetime.now().strftime('%Y%m%d')}.log"
    )

    # 配置日志格式
    log_format = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"

    # 移除默认的处理器
    logger.remove()

    # 添加控制台输出
    logger.add(
        sys.stdout,
        format=log_format,
        level=LOG_LEVEL,
        colorize=True
    )

    # 添加文件输出
    logger.add(
        log_file,
        format=log_format,
        level=LOG_LEVEL,
        rotation="00:00",  # 每天轮换
        retention="30 days",  # 保留30天
        compression="zip",  # 压缩旧日志
        encoding="utf-8"
    )

    logger.info(f"{service_name} 日志系统初始化完成")

def get_logger():
    """获取日志记录器"""
    return logger