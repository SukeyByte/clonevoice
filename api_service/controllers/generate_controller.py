from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import uuid
import json
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
            "status": "pending",
            "text": request.text,
            "video_path": request.video_path,
            "audio_path": request.audio_path
        }
        
        # Store in Redis
        redis_client = RedisClient()
        await redis_client.set(f"task:{task_id}", json.dumps(task_data))
        
        # Send to RabbitMQ
        rabbitmq_client = RabbitMQClient()
        rabbitmq_client.publish(
            "audio_queue",
            "task",
            json.dumps(task_data)
        )
        
        logger.info(f"Created generation task: {task_id}")
        return {"task_id": task_id, "status": "pending"}
        
    except Exception as e:
        logger.error(f"Error creating generation task: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/task/{task_id}")
async def get_task_status(task_id: str):
    try:
        redis_client = RedisClient()
        task_data = await redis_client.get(f"task:{task_id}")
        
        if not task_data:
            raise HTTPException(status_code=404, detail="Task not found")
            
        return json.loads(task_data)
        
    except Exception as e:
        logger.error(f"Error getting task status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))