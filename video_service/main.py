import sys
import os

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from dotenv import load_dotenv
import uvicorn
import json
import os
import cv2
import numpy as np
from threading import Thread

# 导入公共组件
from common.redis_client import RedisClient
from common.rabbitmq_client import RabbitMQClient
from common.logger import setup_logger, get_logger

# 加载环境变量
load_dotenv()

# 初始化日志系统
setup_logger("video_service")
logger = get_logger()

# 创建FastAPI应用
app = FastAPI(title="Video Generation Service", version="1.0.0")

# 初始化RabbitMQ客户端
mq_client = RabbitMQClient()

from video_service.task_handler.video_task_handler import VideoTaskHandler

# 初始化视频任务处理器
video_task_handler = VideoTaskHandler()

def handle_video_task(ch, method, properties, body):
    """处理从消息队列接收到的视频任务"""
    video_task_handler.handle_message(ch, method, properties, body)

@app.on_event("startup")
async def startup_event():
    """服务启动时的处理"""
    try:
        # 确保视频输出目录存在
        os.makedirs("output", exist_ok=True)
        
        # 开始消费视频任务队列
        Thread(target=mq_client.consume, args=("video_tasks", handle_video_task)).start()
        logger.info("视频生成服务启动成功")
    except Exception as e:
        logger.error(f"服务启动失败: {str(e)}")

@app.on_event("shutdown")
async def shutdown_event():
    """服务关闭时的处理"""
    RedisClient.close()
    mq_client.close()
    logger.info("视频生成服务关闭")

if __name__ == "__main__":
    port = int(os.getenv("VIDEO_SERVICE_PORT", 8001))
    uvicorn.run("video_service.main:app", host="0.0.0.0", port=port, reload=True)
    # task = {'task_id': 'fa11e4ed-2ccf-41f6-ba07-105e815bb4d8', 'status': '2', 'text': 'Halo! Selamat datang di sesi pengetahuan finansial bersama kami.', 'video_path': '/home/featurize/clonevoice/uploads/video/347fb1d0-8812-4883-a7dc-82e6df4c1573.mp4', 'audio_path': '/home/featurize/clonevoice/uploads/audio/fdf73042-3459-4958-abf8-44d6b75a0cec.wav', 'audio_output_path': 'output/audio_fa11e4ed-2ccf-41f6-ba07-105e815bb4d8.wav'}
    # video_task_handler.process_video_task(task)