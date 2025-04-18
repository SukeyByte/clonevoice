import json
import os
from pathlib import Path
from threading import Thread
from TTS.api import TTS
from common.redis_client import RedisClient
from common.logger import get_logger
from common.rabbitmq_client import RabbitMQClient
from common.message_pusher import MessagePusher
from audio_service.audio_processor.audio_converter import AudioConverter
from audio_service.audio_processor.text_processor import TextProcessor

logger = get_logger()

class AudioTaskHandler:
    def __init__(self):
        self.redis_client = RedisClient.get_client()
        self.output_dir = Path("output")
        self.temp_dir = self.output_dir / "temp"
        
        # 确保输出目录存在
        self.output_dir.mkdir(exist_ok=True)
        self.temp_dir.mkdir(exist_ok=True)

    def process_audio_task(self, task_data: dict):
        """处理音频生成任务"""
        try:
            task_id = task_data["task_id"]
            task_type = task_data.get("type", "tts")
            logger.info(f"开始处理音频任务: {task_id}, 类型: {task_type}")

            # 更新任务状态为处理中
            task_data["status"] = "1"
            self.redis_client.set(f"task:{task_id}", json.dumps(task_data))

            # 先将参考音频转换为WAV格式
            reference_audio = task_data["audio_path"]
            if reference_audio and not reference_audio.endswith(".wav"):
                wav_reference = self.temp_dir / f"ref_{task_id}.wav"
                if AudioConverter.convert_to_wav(reference_audio, str(wav_reference)):
                    reference_audio = str(wav_reference)
                    task_data["reference_audio_wav"] = str(wav_reference)
                    self.redis_client.set(f"task:{task_id}", json.dumps(task_data))

            # 初始化TTS引擎
            tts = TTS(
                model_path="/home/featurize/training/tts_models/nl/mozilla/xtts/",
                config_path="/home/featurize/training/tts_models/nl/mozilla/xtts/config.json"
            )

            # 分段处理文本
            text = task_data.get("text", "")
            segments = TextProcessor.split_text(text)
            segment_files = []

            for i, segment in enumerate(segments):
                if not segment:
                    continue
                print(segment)
                # 生成每个分段的临时文件路径
                temp_path = self.temp_dir / f"segment_{task_id}_{i}.wav"
                
                # 根据任务类型生成音频
                tts.tts_to_file(
                        text=segment,
                        file_path=str(temp_path),
                        speaker_wav=reference_audio,
                        language="nl",
                    )
                
                segment_files.append(str(temp_path))

            # 合并所有音频片段
            final_output = self.output_dir / f"audio_{task_id}.wav"
            if len(segment_files) > 1:
                success = AudioConverter.merge_audio_files(segment_files, str(final_output))
            elif len(segment_files) == 1:
                # 如果只有一个片段，直接重命名
                os.rename(segment_files[0], str(final_output))
                success = True
            else:
                success = False

            if success:
                # 更新任务状态为完成
                task_data["status"] = "2"
                task_data["output_path"] = str(final_output)
                self.redis_client.set(f"task:{task_id}", json.dumps(task_data))

                # 发送SSE通知
                MessagePusher.push_message(task_id,"audio_task_completed","1")

                # 发送MQ消息通知视频服务
                rabbitmq_client = RabbitMQClient()
                rabbitmq_client.declare_exchange("ai_service")
                rabbitmq_client.declare_queue("video_tasks")
                rabbitmq_client.bind_queue("video_tasks", "ai_service", "video_tasks")
                rabbitmq_client.publish(
                    exchange="ai_service",
                    routing_key="video_tasks",
                    message=json.dumps(task_data)
                )

                # 发送MQ消息通知API服务
                rabbitmq_client.publish(
                    exchange="",
                    routing_key="api_queue",
                    message=json.dumps({
                        "task_id": task_id,
                        "status": "completed",
                        "output_path": str(final_output),
                        "type": "audio_task_update"
                    })
                )

                logger.info(f"音频克隆任务完成: {task_id}")

                # 清理临时文件
                for file in segment_files:
                    try:
                        os.remove(file)
                    except Exception as e:
                        logger.warning(f"清理临时文件失败: {str(e)}")
            else:
                raise Exception("音频处理失败")

        except Exception as e:
            logger.error(f"音频克隆任务失败: {str(e)}")
            task_data["status"] = "failed"
            task_data["error"] = str(e)
            self.redis_client.set(f"task:{task_id}", json.dumps(task_data))

    def handle_message(self, ch, method, properties, body):
        """处理从消息队列接收到的音频任务"""
        try:
            print(f"收到消息:{body}")
            task_data = json.loads(body)
            # 在新线程中处理任务，避免阻塞消息队列
            self.process_audio_task(task_data)
        except Exception as e:
            logger.error(f"处理音频任务消息失败: {str(e)}")
