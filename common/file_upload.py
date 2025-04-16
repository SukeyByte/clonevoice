import os
import uuid
from typing import Optional, List, Dict
from fastapi import UploadFile, HTTPException
from pathlib import Path

class FileUploadManager:
    # 允许的文件类型
    ALLOWED_AUDIO_TYPES = ['.mp3', '.wav', '.ogg', '.m4a']
    ALLOWED_VIDEO_TYPES = ['.mp4', '.avi', '.mov', '.mkv']
    
    # 文件大小限制（单位：字节）
    MAX_AUDIO_SIZE = 50 * 1024 * 1024  # 50MB
    MAX_VIDEO_SIZE = 500 * 1024 * 1024  # 500MB
    
    def __init__(self, base_upload_path: str):
        """初始化文件上传管理器
        
        Args:
            base_upload_path (str): 基础上传路径
        """
        self.base_upload_path = base_upload_path
        self._ensure_upload_dirs()
    
    def _ensure_upload_dirs(self):
        """确保上传目录存在"""
        for dir_type in ['audio', 'video']:
            path = os.path.join(self.base_upload_path, dir_type)
            os.makedirs(path, exist_ok=True)
    
    def _validate_file_type(self, filename: str, file_type: str) -> bool:
        """验证文件类型
        
        Args:
            filename (str): 文件名
            file_type (str): 文件类型（'audio' 或 'video'）
        
        Returns:
            bool: 是否是允许的文件类型
        """
        ext = os.path.splitext(filename)[1].lower()
        if file_type == 'audio':
            return ext in self.ALLOWED_AUDIO_TYPES
        elif file_type == 'video':
            return ext in self.ALLOWED_VIDEO_TYPES
        return False
    
    def _validate_file_size(self, file_size: int, file_type: str) -> bool:
        """验证文件大小
        
        Args:
            file_size (int): 文件大小（字节）
            file_type (str): 文件类型（'audio' 或 'video'）
        
        Returns:
            bool: 是否在允许的大小范围内
        """
        if file_type == 'audio':
            return file_size <= self.MAX_AUDIO_SIZE
        elif file_type == 'video':
            return file_size <= self.MAX_VIDEO_SIZE
        return False
    
    async def save_file(self, file: UploadFile, file_type: str) -> Dict:
        """保存上传的文件
        
        Args:
            file (UploadFile): 上传的文件
            file_type (str): 文件类型（'audio' 或 'video'）
        
        Returns:
            Dict: 包含文件信息的字典
        
        Raises:
            HTTPException: 当文件类型或大小不符合要求时抛出异常
        """
        if not self._validate_file_type(file.filename, file_type):
            raise HTTPException(status_code=400, detail=f"不支持的{file_type}文件类型")
        
        content = await file.read()
        file_size = len(content)
        
        if not self._validate_file_size(file_size, file_type):
            raise HTTPException(status_code=400, detail=f"{file_type}文件大小超过限制")
        
        # 生成唯一文件名
        ext = os.path.splitext(file.filename)[1]
        unique_filename = f"{str(uuid.uuid4())}{ext}"
        
        # 构建保存路径
        save_path = os.path.join(self.base_upload_path, file_type, unique_filename)
        
        # 保存文件
        with open(save_path, 'wb') as f:
            f.write(content)
        
        return {
            'original_filename': file.filename,
            'saved_filename': unique_filename,
            'file_type': file_type,
            'file_size': file_size,
            'file_path': save_path
        }
    
    def get_file_path(self, filename: str, file_type: str) -> Optional[str]:
        """获取文件路径
        
        Args:
            filename (str): 文件名
            file_type (str): 文件类型（'audio' 或 'video'）
        
        Returns:
            Optional[str]: 文件路径，如果文件不存在则返回None
        """
        file_path = os.path.join(self.base_upload_path, file_type, filename)
        return file_path if os.path.exists(file_path) else None