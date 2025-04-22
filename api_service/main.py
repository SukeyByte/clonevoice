import sys
import os
import asyncio
from threading import Thread
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse
import uvicorn
import json
from dotenv import load_dotenv
from fastapi.openapi.utils import get_openapi
from typing import Dict, Set
from collections import defaultdict

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入公共组件
from common.redis_client import RedisClient
from common.rabbitmq_client import RabbitMQClient
from common.logger import setup_logger, get_logger

# 导入控制器
from api_service.controllers.video_controller import router as video_router
from api_service.controllers.audio_controller import router as audio_router
from api_service.controllers.generate_controller import router as generate_router

# 加载环境变量
load_dotenv()

# 初始化日志系统
setup_logger("api_service")
logger = get_logger()

# 创建FastAPI应用

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("API服务启动")
    loop = asyncio.get_event_loop()
    loop.create_task(handle_mq_messages())  # 启动消息监听
    yield
    mq_client.close()
    RedisClient.close()
    logger.info("API服务关闭")

app = FastAPI(title="AI Service API", version="1.0.0")

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="/home/featurize/clonevoice/uploads"), name="static")

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
app.include_router(generate_router)

# 存储所有活跃的SSE连接
connected_clients: Set[asyncio.Queue] = set()

async def broadcast_message(message: dict):
    print(message)
    """广播消息到所有连接的客户端"""
    for queue in connected_clients:
        await queue.put(message)

# 处理来自RabbitMQ的消息
async def handle_mq_messages():
    """消息处理后台任务"""
    try:
        def callback(ch, method, properties, body):
            message = json.loads(body)
            asyncio.create_task(broadcast_message({
                "event_type": "message", 
                "message": message
            }))
            
        # 确保队列和绑定都正确设置
        mq_client.declare_queue("api_tasks")
        mq_client.bind_queue("api_tasks", "ai_service", "api_tasks")
        mq_client.consume("api_tasks", callback)
        # 保持连接存活
        while True:
            await asyncio.sleep(1)
            
    except Exception as e:
        logger.error(f"消息处理错误: {str(e)}")
        # 重新连接
        mq_client.reconnect()

@app.post("/send_event")
async def send_event(request: Request):
    print(request)
    """模拟推送事件接口"""
    try:
        message = await request.json()
        if not connected_clients:
            return JSONResponse(content={"status": "No connected clients."})
        
        # 广播消息给所有客户端
        await broadcast_message(message)
        
        return JSONResponse(content={"status": "Message sent.", "message": message})
    
    except Exception as e:
        return JSONResponse(content={"status": "error", "detail": str(e)}, status_code=500)
    
@app.get("/events")
async def events():
    """SSE事件流接口"""
    async def event_generator():
        # 为每个连接创建一个消息队列
        queue = asyncio.Queue()
        connected_clients.add(queue)
        
        try:
            while True:
                # 等待消息
                message = await queue.get()
                if message:
                    yield {
                        "event": message.get("event_type", "status"),
                        "data": json.dumps(message)
                    }
                    
        except Exception as e:
            logger.error(f"SSE连接错误: {str(e)}")
        finally:
            # 清理连接
            connected_clients.remove(queue)
    
    return EventSourceResponse(event_generator())

def custom_openapi():
    """自定义OpenAPI文档"""
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="AI Service API",
        version="1.0.0",
        description="This is the API documentation for the AI Service, providing endpoints for video and audio processing.",
        routes=app.routes,
    )
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi


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
    print("服务启动", flush=True)
    uvicorn.run("api_service.main:app", host="0.0.0.0", port=port, reload=True)
    logger.info("API服务启动启动成功")        