import os
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File
from sqlalchemy.orm import Session
import json
import uuid

from common.database import get_db
from common.redis_client import RedisClient
from common.rabbitmq_client import RabbitMQClient
from common.logger import get_logger
from common.file_upload import FileUploadManager

router = APIRouter(prefix="/audio", tags=["audio"])
logger = get_logger()
mq_client = RabbitMQClient()

base_path = '/home/featurize/clonevoice/uploads'

@router.post("/upload")
async def upload_audio(file: UploadFile = File(...)):
    """Upload audio file and return saved path"""
    try:
        # Save uploaded audio file
        upload_manager = FileUploadManager(base_path)
        file_info = await upload_manager.save_file(file, 'audio')
        
        return {
            "status": "success",
            "file_path": file_info["file_path"]
        }
        
    except Exception as e:
        logger.error(f"Error uploading audio: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/clone")
async def clone_audio(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """克隆音频的API接口"""
    try:
        # 创建音频克隆任务
        task_id = "audio_" + str(uuid.uuid4())
        task_data = {
            "task_id": task_id,
            "status": "pending"
        }
        
        # 将任务信息存入Redis
        redis_client = RedisClient.get_client()
        redis_client.set(f"task:{task_id}", json.dumps(task_data))
        
        # 发送任务到音频服务
        mq_client.publish(
            exchange="ai_service",
            routing_key="audio",
            message=json.dumps(task_data)
        )
        
        return {"task_id": task_id, "message": "音频克隆任务已提交"}
    except Exception as e:
        logger.error(f"提交音频克隆任务失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/list")
async def list_audios(
    page: int = 1,
    page_size: int = 10,
    start_time: str = None,
    end_time: str = None
):
    """List all audio files with pagination"""
    try:
        audio_path = base_path + '/audio'
        if not os.path.exists(audio_path):
            return {
                "status": "success",
                "total": 0,
                "page": page,
                "page_size": page_size,
                "data": []
            }

        audio_files = []
        for filename in os.listdir(audio_path):
            file_path = os.path.join(audio_path, filename)
            stats = os.stat(file_path)
            
            file_info = {
                "filename": filename,
                "file_path": file_path,
                "size": stats.st_size,
                "created_at": datetime.fromtimestamp(stats.st_ctime).isoformat(),
                "modified_at": datetime.fromtimestamp(stats.st_mtime).isoformat()
            }
            
            # Apply time filters if specified
            if start_time and file_info["created_at"] < start_time:
                continue
            if end_time and file_info["created_at"] > end_time:
                continue
                
            audio_files.append(file_info)

        # Sort by creation time
        audio_files.sort(key=lambda x: x["created_at"], reverse=True)
        
        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_files = audio_files[start_idx:end_idx]
        
        return {
            "status": "success",
            "total": len(audio_files),
            "page": page,
            "page_size": page_size,
            "data": paginated_files
        }
        
    except Exception as e:
        logger.error(f"Error listing audio files: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))