import time
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import uuid
import json
from typing import List, Optional
from common.redis_client import RedisClient
from common.rabbitmq_client import RabbitMQClient
from common.logger import get_logger

router = APIRouter(prefix="/generate", tags=["generate"])
logger = get_logger()

class GenerationRequest(BaseModel):
    text: str
    video_path: str
    audio_path: str

@router.post("/task")
async def create_generation_task(request: GenerationRequest):
    try:
        # Generate unique task ID
        task_id = str(uuid.uuid4())
        
        # Create task data
        task_data = {
            "task_id": task_id,
            "status": "0",
            "text": request.text,
            "video_path": request.video_path,
            "audio_path": request.audio_path,
            "create_time": int(time.time()),
        }
        
        # Store in Redis
        redis_client = RedisClient()
        redis_client.set(f"task:{task_id}", json.dumps(task_data))
        
        # Send to RabbitMQ
        rabbitmq_client = RabbitMQClient()

        rabbitmq_client.declare_exchange("ai_service")
        rabbitmq_client.declare_queue("audio_tasks")
        rabbitmq_client.bind_queue("audio_tasks", "ai_service", "audio_tasks")

        rabbitmq_client.publish(
            "ai_service",
            "audio_tasks",
            json.dumps(task_data)
        )
        
        logger.info(f"Created generation task: {task_id}")
        return {"task_id": task_id, "status": "0"}# status 0 start, 1 audio start 2 video start 3 finish
        
    except Exception as e:
        logger.error(f"Error creating generation task: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/task/{task_id}")
async def get_task_status(task_id: str):
    try:
        redis_client = RedisClient()
        task_data = redis_client.get(f"task:{task_id}")
        
        if not task_data:
            raise HTTPException(status_code=404, detail="Task not found")
            
        return json.loads(task_data)
        
    except Exception as e:
        logger.error(f"Error getting task status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tasks", response_model=dict)
async def list_tasks(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=10, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(default=None, description="Filter by status (0,1,2,3)")
):
    """
    Get paginated list of generation tasks
    - status: 0=start, 1=audio start, 2=video start, 3=finish
    """
    try:
        redis_client = RedisClient()
        # Get all task keys
        task_keys = redis_client.scan_keys("task:*")

        tasks = []
        # Fetch task data for each key
        for key in task_keys:
            task_data = redis_client.get(key)
            print(task_data)
            if task_data:
                task = json.loads(task_data)
                tasks.append(task)
        
        # Sort tasks by creation time (newest first)
        tasks.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_tasks = tasks[start_idx:end_idx]
        
        return {
            "total": len(tasks),
            "page": page,
            "page_size": page_size,
            "data": paginated_tasks
        }
        
    except Exception as e:
        logger.error(f"Error listing tasks: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))