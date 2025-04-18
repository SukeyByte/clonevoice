import sys
import os

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from dotenv import load_dotenv
import uvicorn
import os
from pathlib import Path
from threading import Thread

# 导入公共组件
from common.redis_client import RedisClient
from common.rabbitmq_client import RabbitMQClient
from common.logger import setup_logger, get_logger
from audio_service.task_handler.audio_task_handler import AudioTaskHandler

# 加载环境变量
load_dotenv()

# 初始化日志系统
setup_logger("audio_service")
logger = get_logger()

# 创建FastAPI应用
app = FastAPI(title="Audio Clone Service", version="1.0.0")

# 初始化RabbitMQ客户端和音频任务处理器
mq_client = RabbitMQClient()
task_handler = AudioTaskHandler()

@app.on_event("startup")
async def startup_event():
    """服务启动时的处理"""
    try:
        # 确保音频输出目录存在
        os.makedirs("output", exist_ok=True)
        os.makedirs("output/temp", exist_ok=True)
        
        # 开始消费音频任务队列
        Thread(target=mq_client.consume, args=("audio_tasks", task_handler.handle_message)).start()
        logger.info("音频克隆服务启动成功")
    except Exception as e:
        logger.error(f"服务启动失败: {str(e)}")

@app.on_event("shutdown")
async def shutdown_event():
    """服务关闭时的处理"""
    RedisClient.close()
    mq_client.close()
    logger.info("音频克隆服务关闭")

if __name__ == "__main__":
    port = int(os.getenv("AUDIO_SERVICE_PORT", 8002))
    uvicorn.run("audio_service.main:app", host="0.0.0.0", port=port, reload=True)