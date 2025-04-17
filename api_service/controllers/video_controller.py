from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File
from sqlalchemy.orm import Session
import json
import uuid
import os
from datetime import datetime

from common.database import get_db
from common.redis_client import RedisClient
from common.rabbitmq_client import RabbitMQClient
from common.logger import get_logger
from common.file_upload import FileUploadManager

router = APIRouter(prefix="/video", tags=["video"])
logger = get_logger()
mq_client = RabbitMQClient()

base_path = '/home/featurize/clonevoice/uploads'

@router.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    """Upload video file and return saved path"""
    try:
        upload_manager = FileUploadManager(base_path)
        file_info = await upload_manager.save_file(file, 'video')
        
        return {
            "status": "success",
            "file_path": file_info["file_path"]
        }
        
    except Exception as e:
        logger.error(f"Error uploading video: {str(e)}")
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
    start_time: str = None,
    end_time: str = None
):
    """List all video files with pagination"""
    try:
        video_path = base_path + '/video'
        if not os.path.exists(video_path):
            return {
                "status": "success",
                "total": 0,
                "page": page,
                "page_size": page_size,
                "data": []
            }

        video_files = []
        for filename in os.listdir(video_path):
            file_path = os.path.join(video_path, filename)
            stats = os.stat(file_path)
            
            file_info = {
                "filename": filename,
                "file_path": file_path,
                "size": stats.st_size,
                "created_at": datetime.fromtimestamp(stats.st_ctime).isoformat(),
                "modified_at": datetime.fromtimestamp(stats.st_mtime).isoformat()
            }
            
            # Apply time filters
            if start_time and file_info["created_at"] < start_time:
                continue
            if end_time and file_info["created_at"] > end_time:
                continue
                
            video_files.append(file_info)

        # Sort by creation time
        video_files.sort(key=lambda x: x["created_at"], reverse=True)
        
        # Pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_files = video_files[start_idx:end_idx]
        
        return {
            "status": "success",
            "total": len(video_files),
            "page": page,
            "page_size": page_size,
            "data": paginated_files
        }
        
    except Exception as e:
        logger.error(f"Error listing video files: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))