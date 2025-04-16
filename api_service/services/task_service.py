from common.redis_client import RedisClient
from common.rabbitmq_client import RabbitMQClient
from common.logger import get_logger
import json
import uuid

logger = get_logger()
mq_client = RabbitMQClient()

class TaskService:
    @staticmethod
    def create_task(task_type: str, file_info: dict = None) -> dict:
        """创建任务并发送到消息队列"""
        try:
            # 生成任务ID
            task_id = f"{task_type}_{str(uuid.uuid4())}"
            
            # 创建任务数据
            task_data = {
                "task_id": task_id,
                "status": "pending"
            }
            
            # 如果有文件信息，添加到任务数据中
            if file_info:
                task_data["file_info"] = file_info
            
            # 将任务信息存入Redis
            redis_client = RedisClient.get_client()
            redis_client.set(f"task:{task_id}", json.dumps(task_data))
            
            # 发送任务到对应的服务
            mq_client.publish(
                exchange="ai_service",
                routing_key=task_type,
                message=json.dumps(task_data)
            )
            
            return task_data
        except Exception as e:
            logger.error(f"创建任务失败: {str(e)}")
            raise
    
    @staticmethod
    def get_task_status(task_id: str) -> dict:
        """获取任务状态"""
        try:
            redis_client = RedisClient.get_client()
            task_data = redis_client.get(f"task:{task_id}")
            
            if task_data:
                return json.loads(task_data)
            return None
        except Exception as e:
            logger.error(f"获取任务状态失败: {str(e)}")
            raise