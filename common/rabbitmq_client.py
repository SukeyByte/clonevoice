import pika
from typing import Callable, Optional
from dotenv import load_dotenv
import os
from loguru import logger

# 加载环境变量
load_dotenv()

# RabbitMQ配置
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", 5672))
RABBITMQ_USER = os.getenv("RABBITMQ_USER")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD")

class RabbitMQClient:
    def __init__(self):
        self.connection = None
        self.channel = None
        self.connect()

    def connect(self) -> None:
        """连接到RabbitMQ服务器"""
        credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
        parameters = pika.ConnectionParameters(
            host=RABBITMQ_HOST,
            port=RABBITMQ_PORT,
            credentials=credentials
        )
        self.connection = pika.BlockingConnection(parameters)
        self.channel = self.connection.channel()

    def publish(self, exchange: str, routing_key: str, message: str) -> None:
        """发布消息到指定的交换机和路由键"""
        try:
            if not self.connection or self.connection.is_closed:
                self.connect()
            self.channel.basic_publish(
                exchange=exchange,
                routing_key=routing_key,
                body=message
            )
            logger.info(f"消息已发送到 {exchange}:{routing_key}")
        except Exception as e:
            logger.error(f"发送消息失败: {str(e)}")
            self.reconnect()

    def consume(self, queue: str, callback: Callable) -> None:
        """从指定队列消费消息"""
        try:
            self.channel.basic_consume(
                queue=queue,
                on_message_callback=callback,
                auto_ack=True
            )
            logger.info(f"开始监听队列: {queue}")
            self.channel.start_consuming()
        except Exception as e:
            logger.error(f"消费消息失败: {str(e)}")
            self.reconnect()

    def declare_exchange(self, exchange: str, exchange_type: str = 'direct') -> None:
        """声明交换机"""
        self.channel.exchange_declare(
            exchange=exchange,
            exchange_type=exchange_type,
            durable=True
        )

    def declare_queue(self, queue: str) -> None:
        """声明队列"""
        self.channel.queue_declare(queue=queue, durable=True)

    def bind_queue(self, queue: str, exchange: str, routing_key: str) -> None:
        """绑定队列到交换机"""
        self.channel.queue_bind(
            queue=queue,
            exchange=exchange,
            routing_key=routing_key
        )

    def reconnect(self) -> None:
        """重新连接到RabbitMQ服务器"""
        try:
            if self.connection and not self.connection.is_closed:
                self.connection.close()
            self.connect()
        except Exception as e:
            logger.error(f"重新连接失败: {str(e)}")

    def close(self) -> None:
        """关闭连接"""
        if self.connection and not self.connection.is_closed:
            self.connection.close()