import json
import os
from pathlib import Path
from threading import Thread
from common.redis_client import RedisClient
from common.logger import get_logger
from common.message_pusher import MessagePusher
from common.rabbitmq_client import RabbitMQClient

logger = get_logger()

class VideoTaskHandler:
    def __init__(self):
        self.redis_client = RedisClient.get_client()
        self.output_dir = Path("uploads/out_video")
        self.temp_dir = self.output_dir / "temp"
        self.video_dir = Path("videos")
        
        # 确保目录存在
        self.output_dir.mkdir(exist_ok=True)
        self.temp_dir.mkdir(exist_ok=True)
        self.video_dir.mkdir(exist_ok=True)
        
    def process_video_task(self, task_data: dict):
        """处理视频生成任务"""
        try:
            task_id = task_data["task_id"]
            video_path = task_data.get("video_path")
            audio_path = task_data.get("audio_output_path")  # 使用生成的音频路径
            
            logger.info(f"开始处理视频生成任务: {task_id}")

            # 更新任务状态为处理中
            MessagePusher.push_message(task_id, "video_start","2")

            # 验证输入文件
            if not audio_path or not os.path.exists(audio_path):
                raise Exception("生成的音频文件不存在")
            if not video_path or not os.path.exists(video_path):
                raise Exception("视频文件不存在")

            # 生成输出文件路径
            output_path = self.output_dir / f"video_{task_id}.mp4"

            # 生成唇形同步视频
            MessagePusher.push_message(task_id, "video_generating","3")
            print(output_path)
            self._generate_sync_video(
                audio_path=audio_path,
                video_path=video_path,
                output_path=str(output_path)
            )

            # 更新任务状态为完成
            task_data["video_output_path"] = str(output_path)
            task_data["status"] = "4"
            task_data["end_time"] = "4"
            MessagePusher.push_message(task_id, "video_done","4")

            rabbitmq_client = RabbitMQClient()
            rabbitmq_client.declare_exchange("ai_service")
            rabbitmq_client.declare_queue("api_tasks")
            rabbitmq_client.bind_queue("api_tasks", "ai_service", "api_tasks")
            rabbitmq_client.publish(
                    exchange="ai_service",
                    routing_key="api_tasks",
                    message=json.dumps(task_data)
                )
            
            logger.info(f'task_data:{task_data}')
            self.redis_client.set(f"task:{task_id}", json.dumps(task_data))
            logger.info(f"视频生成任务完成: {task_id}")

        except Exception as e:
            logger.error(f"视频生成任务失败: {str(e)}")
            MessagePusher.push_message(task_id, "video_done" , "4")

    def _generate_sync_video(self, audio_path: str, video_path: str, output_path: str):
        """使用LatentSync模型生成唇形同步的视频"""
        try:
            from .latent_sync_generator import LatentSyncGenerator
            # 创建临时输出目录
            temp_dir = Path("./temp")
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            # 配置生成参数
            guidance_scale = 1  # 控制生成效果的指导尺度
            inference_steps = 20  # 推理步数
            seed = 42  # 随机种子，保证结果可复现
            
            # 初始化生成器并处理视频
            generator = LatentSyncGenerator()
            
            generator.process_video(
                video_path=video_path,
                audio_path=audio_path,
                output_path=str(output_path),
                guidance_scale=guidance_scale,
                inference_steps=inference_steps,
                seed=seed
            )
            print(f"video_path:{video_path}")
            logger.info(f"成功生成唇形同步视频: {output_path}")
            
        except ImportError as e:
            logger.error(f"LatentSync模型导入失败，请确保已安装所有依赖: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"生成同步视频失败: {str(e)}")
            raise

    def handle_message(self, ch, method, properties, body):
        """处理从消息队列接收到的视频任务"""
        try:
            task_data = json.loads(body)
            print(task_data)
            # 在新线程中处理任务，避免阻塞消息队列
            self.process_video_task(task_data)
        except Exception as e:
            logger.error(f"处理视频任务消息失败: {str(e)}")
