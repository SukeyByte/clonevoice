import json
import requests
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from common.redis_client import RedisClient
from common.logger import get_logger

logger = get_logger()

class MessagePusher:
    def send_event_notification(self, task_id: str) -> bool:
        """
        发送事件通知到本地API服务
        """
        try:            
            response = requests.post(
                "http://localhost:8000/send_event",
                json={'message':task_id}
            )

            if response.status_code == 200:
                logger.info(f"事件通知发送成功: {task_id}")
                return True
            else:
                logger.error(f"事件通知发送失败: {task_id} - 状态码: {response.status_code}")
                return False
                    
        except Exception as e:
            logger.error(f"事件通知发送失败: {task_id} - {str(e)}")
            return False

    def push_message(self, task_id: str, message: str, event_type: str = "status") -> bool:
        """
        推送消息到Redis并返回是否成功
        :param task_id: 任务ID
        :param message: 消息内容
        :param event_type: 事件类型
        :return: 是否成功推送
        """
        try:
            # 添加时间戳
            result = {}
            result["timestamp"] = datetime.now().isoformat()
            result["event_type"] = event_type
            result["message"] = message
            
            # 存储到Redis
            redis_key = f"message:{task_id}"
            redis_client = RedisClient.get_client()
            redis_client.set(
                redis_key,
                json.dumps(result)
            )

            # 创建事件循环来运行异步方法
            message_pusher.send_event_notification(task_id)

            logger.info(f"消息推送成功: {task_id} - {message}")
            return True
        except Exception as e:
            logger.error(f"消息推送失败: {task_id} - {str(e)}")
            return False
    
    def get_message(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        从Redis获取消息
        :param task_id: 任务ID
        :return: 消息内容或None
        """
        try:
            redis_key = f"task:{task_id}"
            message_data = self.redis_client.get(redis_key)
            
            if message_data:
                return json.loads(message_data)
            return None
        except Exception as e:
            logger.error(f"获取消息失败: {task_id} - {str(e)}")
            return None
    
    def delete_message(self, task_id: str) -> bool:
        """
        从Redis删除消息
        :param task_id: 任务ID
        :return: 是否成功删除
        """
        try:
            redis_key = f"task:{task_id}"
            self.redis_client.delete(redis_key)
            return True
        except Exception as e:
            logger.error(f"删除消息失败: {task_id} - {str(e)}")
            return False

# 创建全局消息推送器实例
message_pusher = MessagePusher()