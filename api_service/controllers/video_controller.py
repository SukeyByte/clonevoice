from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File
from sqlalchemy.orm import Session
import json
import uuid

from common.database import get_db
from common.redis_client import RedisClient
from common.rabbitmq_client import RabbitMQClient
from common.logger import get_logger
from common.file_upload import FileUploadManager

router = APIRouter(prefix="/video", tags=["video"])
logger = get_logger()
mq_client = RabbitMQClient()

@router.post("/upload")
async def upload_video(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """上传视频文件的API接口"""
    try:
        # 保存上传的视频文件
        upload_manager = FileUploadManager()
        file_info = await upload_manager.save_file(file, 'video')
        
        # 创建视频生成任务
        task_id = "video_" + str(uuid.uuid4())
        task_data = {
            "task_id": task_id,
            "status": "pending",
            "file_info": file_info
        }
        
        # 将任务信息存入Redis
        redis_client = RedisClient.get_client()
        redis_client.set(f"task:{task_id}", json.dumps(task_data))
        
        # 发送任务到视频服务
        mq_client.publish(
            exchange="ai_service",
            routing_key="video",
            message=json.dumps(task_data)
        )
        
        return {"task_id": task_id, "message": "视频文件上传成功，生成任务已提交", "file_info": file_info}
    except Exception as e:
        logger.error(f"视频文件上传失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate")
async def generate_video(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """生成视频的API接口"""
    try:
        # 创建视频生成任务
        task_id = "video_" + str(uuid.uuid4())
        task_data = {
            "task_id": task_id,
            "status": "pending"
        }
        
        # 将任务信息存入Redis
        redis_client = RedisClient.get_client()
        redis_client.set(f"task:{task_id}", json.dumps(task_data))
        
        # 发送任务到视频服务
        mq_client.publish(
            exchange="ai_service",
            routing_key="video",
            message=json.dumps(task_data)
        )
        
        return {"task_id": task_id, "message": "视频生成任务已提交"}
    except Exception as e:
        logger.error(f"提交视频生成任务失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/list")
async def list_videos(
    page: int = 1,
    page_size: int = 10,
    status: str = None,
    start_time: str = None,
    end_time: str = None,
    db: Session = Depends(get_db)
):
    """获取视频任务列表"""
    try:
        redis_client = RedisClient.get_client()
        # 构建查询条件
        query_key = f"video_list:{page}:{page_size}"
        if status:
            query_key += f":{status}"
        if start_time:
            query_key += f":{start_time}"
        if end_time:
            query_key += f":{end_time}"
            
        # 尝试从缓存获取结果
        cached_result = redis_client.get(query_key)
        if cached_result:
            return json.loads(cached_result)
            
        # 从Redis中获取所有任务
        tasks = []
        for key in redis_client.scan_iter("task:video_*"):
            task_data = json.loads(redis_client.get(key))
            # 应用过滤条件
            if status and task_data.get("status") != status:
                continue
            tasks.append(task_data)
            
        # 按创建时间倒序排序
        tasks.sort(key=lambda x: x.get("file_info", {}).get("created_at", ""), reverse=True)
        
        # 分页处理
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_tasks = tasks[start_idx:end_idx]
        
        result = {
            "total": len(tasks),
            "page": page,
            "page_size": page_size,
            "data": paginated_tasks
        }
        
        # 缓存结果（设置60秒过期）
        redis_client.setex(query_key, 60, json.dumps(result))
        
        return result
    except Exception as e:
        logger.error(f"获取视频列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))