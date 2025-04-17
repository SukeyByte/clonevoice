from redis import Redis
from dotenv import load_dotenv
import os
from typing import Optional

# 加载环境变量
load_dotenv()

# Redis配置
REDIS_HOST = os.getenv("REDIS_HOST")
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

    async def set(self, key: str, value: str, expire: int = None) -> bool:
        self.get_client()
        try:
            await self.redis.set(key, value)
            if expire:
                await self.redis.expire(key, expire)
            return True
        except Exception as e:
            print(f"Redis set error: {str(e)}")
            return False
            
    async def get(self, key: str) -> Optional[str]:
        self.get_client()
        try:
            value = await self.redis.get(key)
            return value.decode('utf-8') if value else None
        except Exception as e:
            print(f"Redis get error: {str(e)}")
            return None
            
    async def close(self):
        if self.redis:
            self.redis.close()
            await self.redis.wait_closed()