from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
import uvicorn
import json
import os
import asyncio
from dotenv import load_dotenv

# 导入公共组件
from common.redis_client import RedisClient
from common.rabbitmq_client import RabbitMQClient
from common.logger import setup_logger, get_logger

# 导入控制器
from controllers.video_controller import router as video_router
from controllers.audio_controller import router as audio_router

# 加载环境变量
load_dotenv()

# 初始化日志系统
setup_logger("api_service")
logger = get_logger()

# 创建FastAPI应用
app = FastAPI(title="AI Service API", version="1.0.0")

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化RabbitMQ客户端
mq_client = RabbitMQClient()

# 声明交换机和队列
mq_client.declare_exchange("ai_service")
mq_client.declare_queue("video_tasks")
mq_client.declare_queue("audio_tasks")
mq_client.bind_queue("video_tasks", "ai_service", "video")
mq_client.bind_queue("audio_tasks", "ai_service", "audio")

# 注册路由
app.include_router(video_router)
app.include_router(audio_router)

@app.on_event("startup")
async def startup_event():
    logger.info("API服务启动")

@app.on_event("shutdown")
async def shutdown_event():
    RedisClient.close()
    mq_client.close()
    logger.info("API服务关闭")

# 导入消息推送器
from common.message_pusher import message_pusher

@app.get("/task/{task_id}/status")
async def get_task_status(task_id: str):
    """获取任务状态的SSE接口"""
    async def event_generator():
        while True:
            # 从消息推送器获取任务状态
            task_info = message_pusher.get_message(task_id)
            if task_info:
                yield {
                    "event": task_info.get("event_type", "status"),
                    "data": json.dumps(task_info)
                }
                
                # 如果任务完成或失败，结束SSE连接
                if task_info.get("status") in ["completed", "failed"]:
                    break
            
            await asyncio.sleep(1)
    
    return EventSourceResponse(event_generator())

if __name__ == "__main__":
    port = int(os.getenv("API_SERVICE_PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)