from redis import Redis
from dotenv import load_dotenv
import os
from typing import Optional, List

# 加载环境变量
load_dotenv()

# Redis配置
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))

class RedisClient:
    _instance: Optional[Redis] = None

    @classmethod
    def get_client(cls) -> Redis:
        """获取Redis客户端单例"""
        if cls._instance is None:
            cls._instance = Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                decode_responses=True
            )
        return cls._instance

    @classmethod
    def close(cls) -> None:
        """关闭Redis连接"""
        if cls._instance is not None:
            cls._instance.close()
            cls._instance = None

    def set(self, key: str, value: str, expire: int = None) -> bool:
        """设置键值对"""
        try:
            client = self.get_client()
            client.set(key, value)
            if expire:
                client.expire(key, expire)
            return True
        except Exception as e:
            print(f"Redis set error: {str(e)}")
            return False
            
    def get(self, key: str) -> Optional[str]:
        """获取键值"""
        try:
            client = self.get_client()
            return client.get(key)
        except Exception as e:
            print(f"Redis get error: {str(e)}")
            return None

    def scan_keys(self, pattern: str) -> List[str]:
        """通过 scan 获取匹配的键列表"""
        keys = []
        try:
            client = self.get_client()
            cursor = 0
            while True:
                cursor, partial_keys = client.scan(cursor=cursor, match=pattern, count=100)
                keys.extend(partial_keys)
                if cursor == 0:
                    break
        except Exception as e:
            print(f"Redis scan error: {str(e)}")
        return keys
            
    def keys(self, pattern: str) -> List[str]:
        """获取匹配的键列表"""
        try:
            client = self.get_client()
            return client.keys(pattern)
        except Exception as e:
            print(f"Redis keys error: {str(e)}")
            return []

    def close(self):
        """关闭Redis连接"""
        self.close(self)