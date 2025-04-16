import json
import os
from pathlib import Path
from threading import Thread
import cv2
import numpy as np
import torch
from common.redis_client import RedisClient
from common.logger import get_logger
from common.message_pusher import MessagePusher
from common.rabbitmq_client import RabbitMQClient

logger = get_logger()

class VideoTaskHandler:
    def __init__(self):
        self.redis_client = RedisClient.get_client()
        self.output_dir = Path("output")
        self.temp_dir = self.output_dir / "temp"
        self.video_dir = Path("videos")
        
        # 确保目录存在
        self.output_dir.mkdir(exist_ok=True)
        self.temp_dir.mkdir(exist_ok=True)
        self.video_dir.mkdir(exist_ok=True)
        
        # 初始化LatentSync模型
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = self._init_latent_sync_model()

    def _init_latent_sync_model(self):
        """初始化LatentSync模型"""
        try:
            # TODO: 根据实际模型路径和配置进行初始化
            # model = LatentSync(...)
            # model.to(self.device)
            # return model
            pass
        except Exception as e:
            logger.error(f"初始化LatentSync模型失败: {str(e)}")
            raise

    def process_video_task(self, task_data: dict):
        """处理视频生成任务"""
        try:
            task_id = task_data["task_id"]
            audio_path = task_data.get("audio_path")
            video_paths = task_data.get("video_paths", [])
            if isinstance(video_paths, str):
                video_paths = [video_paths]
            
            logger.info(f"开始处理视频生成任务: {task_id}")

            # 更新任务状态为处理中
            task_data["status"] = "processing"
            task_data["progress"] = 10
            message_pusher.push_message(task_id, task_data)

            # 验证输入文件
            if not audio_path or not os.path.exists(audio_path):
                raise Exception("音频文件不存在")
            if not video_paths:
                raise Exception("未提供视频文件")
            for video_path in video_paths:
                if not os.path.exists(video_path):
                    raise Exception(f"视频文件不存在: {video_path}")

            # 生成输出文件路径
            output_path = self.output_dir / f"video_{task_id}.mp4"

            # 加载所有视频帧
            task_data["progress"] = 20
            task_data["message"] = "正在加载视频帧"
            message_pusher.push_message(task_id, task_data)
            video_frames_list = []
            for video_path in video_paths:
                frames = self.model.load_video(video_path)
                video_frames_list.append(frames)

            # 获取音频时长
            audio_duration = librosa.get_duration(path=audio_path)

            # 根据视频数量选择不同的处理方式
            if len(video_frames_list) == 1:
                aligned_frames = self.model.align_single_video(video_frames_list[0], audio_duration)
            else:
                aligned_frames = self.model.align_multiple_videos(video_frames_list, audio_duration)

            # 提取音频特征
            task_data["progress"] = 40
            task_data["message"] = "正在提取音频特征"
            message_pusher.push_message(task_id, task_data)
            mel_features = self.model.extract_audio_features(audio_path)

            # 生成唇形同步视频
            task_data["progress"] = 60
            task_data["message"] = "正在生成唇形同步视频"
            message_pusher.push_message(task_id, task_data)
            sync_frames = self.model.generate_sync_frames(aligned_frames, mel_features)

            # 保存视频
            task_data["progress"] = 80
            task_data["message"] = "正在保存视频"
            message_pusher.push_message(task_id, task_data)
            self.model.save_video(sync_frames, audio_path, str(output_path))

            # 更新任务状态为完成
            task_data["status"] = "completed"
            task_data["output_path"] = str(output_path)
            task_data["progress"] = 100
            task_data["message"] = "视频生成完成"
            message_pusher.push_message(task_id, task_data)

            # 发送SSE通知
            MessagePusher.push_message({
                "type": "video_task_completed",
                "task_id": task_id,
                "status": "completed",
                "output_path": str(output_path)
            })

            # 发送MQ消息通知API服务
            rabbitmq_client = RabbitMQClient()
            rabbitmq_client.publish(
                exchange="",
                routing_key="api_queue",
                message=json.dumps({
                    "task_id": task_id,
                    "status": "completed",
                    "output_path": str(output_path),
                    "type": "video_task_update"
                })
            )

            logger.info(f"视频生成任务完成: {task_id}")

        except Exception as e:
            logger.error(f"视频生成任务失败: {str(e)}")
            task_data["status"] = "failed"
            task_data["error"] = str(e)
            self.redis_client.set(f"task:{task_id}", json.dumps(task_data))

    def _generate_sync_video(self, audio_path: str, video_path: str, output_path: str):
        """使用LatentSync模型生成唇形同步的视频"""
        try:
            from .latent_sync_generator import LatentSyncGenerator
            generator = LatentSyncGenerator(device=self.device)
            generator.generate(video_path, audio_path, output_path)
        except Exception as e:
            logger.error(f"生成同步视频失败: {str(e)}")
            raise

    def handle_message(self, ch, method, properties, body):
        """处理从消息队列接收到的视频任务"""
        try:
            task_data = json.loads(body)
            # 在新线程中处理任务，避免阻塞消息队列
            Thread(target=self.process_video_task, args=(task_data,)).start()
        except Exception as e:
            logger.error(f"处理视频任务消息失败: {str(e)}")