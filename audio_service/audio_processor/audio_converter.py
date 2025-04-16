import subprocess
from common.logger import get_logger

logger = get_logger()

class AudioConverter:
    @staticmethod
    def convert_to_wav(input_path: str, output_path: str) -> bool:
        """将音频转换为WAV格式"""
        try:
            command = [
                'ffmpeg',
                '-i', input_path,
                '-acodec', 'pcm_s16le',
                '-ar', '44100',
                '-ac', '2',
                '-y',
                output_path
            ]
            subprocess.run(command, check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"音频转换失败: {str(e)}")
            return False

    @staticmethod
    def merge_audio_files(input_files: list, output_file: str) -> bool:
        """合并多个音频文件"""
        try:
            # 创建文件列表
            with open('temp_files.txt', 'w', encoding='utf-8') as f:
                for file in input_files:
                    f.write(f"file '{file}'\n")

            # 使用ffmpeg合并文件
            command = [
                'ffmpeg',
                '-f', 'concat',
                '-safe', '0',
                '-i', 'temp_files.txt',
                '-c', 'copy',
                '-y',
                output_file
            ]
            subprocess.run(command, check=True, capture_output=True)
            
            # 清理临时文件
            import os
            os.remove('temp_files.txt')
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"音频合并失败: {str(e)}")
            return False