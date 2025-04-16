import os
import cv2
import torch
import numpy as np
import librosa
from typing import List, Tuple
from pathlib import Path
from common.logger import get_logger

logger = get_logger()

class LatentSyncGenerator:
    def __init__(self, device=None):
        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.mel_step_size = 16
        self.fps = 25
        
    def load_video(self, video_path: str) -> Tuple[np.ndarray, List[np.ndarray]]:
        """加载视频文件，返回视频帧"""
        if not os.path.isfile(video_path):
            raise FileNotFoundError(f"视频文件不存在: {video_path}")

        cap = cv2.VideoCapture(video_path)
        frames = []

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            frames.append(frame)

        cap.release()
        return np.array(frames)

    def extract_audio_features(self, audio_path: str) -> np.ndarray:
        """提取音频特征"""
        if not os.path.isfile(audio_path):
            raise FileNotFoundError(f"音频文件不存在: {audio_path}")

        # 加载音频文件
        y, sr = librosa.load(audio_path, sr=16000)

        # 提取梅尔频谱图特征
        mel_basis = librosa.filters.mel(sr=16000, n_fft=1024, n_mels=80)
        hann_window = torch.hann_window(1024).to(self.device)

        y = torch.FloatTensor(y).to(self.device)
        y = torch.nn.functional.pad(y.unsqueeze(0), (512, 512), mode='reflect')
        y = y.squeeze(0)

        spec = torch.stft(
            y,
            n_fft=1024,
            hop_length=256,
            win_length=1024,
            window=hann_window,
            center=False,
            return_complex=False
        )
        spec = torch.sqrt(spec.pow(2).sum(-1) + 1e-6)

        # 转换为梅尔频谱图
        mel = torch.matmul(mel_basis.to(self.device), spec)
        mel = torch.log(torch.clamp(mel, min=1e-5))

        return mel.cpu().numpy()

    def process_face(self, frame: np.ndarray) -> np.ndarray:
        """处理人脸区域"""
        # 使用预训练的人脸检测模型检测人脸
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)

        if len(faces) == 0:
            return frame

        # 获取最大的人脸区域
        x, y, w, h = max(faces, key=lambda x: x[2] * x[3])
        face_region = frame[y:y+h, x:x+w]

        # 调整人脸大小为模型所需的输入尺寸
        face_region = cv2.resize(face_region, (256, 256))
        return face_region

    def align_single_video(self, video_frames: np.ndarray, audio_duration: float) -> np.ndarray:
        """将单个视频与音频对齐，如果音频较长则翻转并拼接视频"""
        video_duration = len(video_frames) / self.fps
        
        # 如果视频时长足够，直接截取所需部分
        if video_duration >= audio_duration:
            required_frames = int(audio_duration * self.fps)
            return video_frames[:required_frames]
        
        # 如果视频较短，需要翻转并拼接
        final_frames = list(video_frames)
        reversed_frames = list(video_frames[::-1])
        
        while len(final_frames) / self.fps < audio_duration:
            if len(final_frames) / self.fps + video_duration <= audio_duration:
                final_frames.extend(video_frames)
            else:
                final_frames.extend(reversed_frames)
        
        required_frames = int(audio_duration * self.fps)
        return np.array(final_frames[:required_frames])

    def align_multiple_videos(self, video_frames_list: List[np.ndarray], audio_duration: float) -> np.ndarray:
        """将多个视频剪辑并拼接，使其与音频时长对齐"""
        total_frames = []
        required_frames = int(audio_duration * self.fps)
        
        # 计算每个视频应该贡献的帧数
        total_available_frames = sum(len(frames) for frames in video_frames_list)
        for frames in video_frames_list:
            # 按比例分配每个视频的帧数
            video_contribution = int((len(frames) / total_available_frames) * required_frames)
            # 确保至少使用一帧
            video_contribution = max(1, min(video_contribution, len(frames)))
            # 均匀采样帧
            indices = np.linspace(0, len(frames)-1, video_contribution, dtype=int)
            total_frames.extend(frames[indices])
        
        # 调整最终帧数以精确匹配所需时长
        if len(total_frames) > required_frames:
            total_frames = total_frames[:required_frames]
        elif len(total_frames) < required_frames:
            # 如果帧数不足，重复最后一帧
            while len(total_frames) < required_frames:
                total_frames.append(total_frames[-1])
        
        return np.array(total_frames)

    def generate_sync_frames(self, video_frames: np.ndarray, mel_features: np.ndarray) -> List[np.ndarray]:
        """生成唇形同步的视频帧"""
        sync_frames = []
        frame_idx = 0

        for i in range(0, len(mel_features), self.mel_step_size):
            if frame_idx >= len(video_frames):
                break

            frame = video_frames[frame_idx]
            face_region = self.process_face(frame)

            # 获取当前时间点的音频特征
            current_mel = mel_features[i:i+self.mel_step_size]
            if len(current_mel) < self.mel_step_size:
                break

            # TODO: 使用LatentSync模型生成唇形同步的人脸
            # synced_face = self.model(face_region, current_mel)
            synced_face = face_region  # 临时使用原始帧

            # 将生成的人脸区域合并回原始帧
            sync_frames.append(synced_face)
            frame_idx += 1

        return sync_frames

    def save_video(self, frames: List[np.ndarray], audio_path: str, output_path: str):
        """保存生成的视频"""
        if not frames:
            raise ValueError("没有可用的视频帧")

        # 创建视频写入器
        height, width = frames[0].shape[:2]
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, self.fps, (width, height))

        # 写入视频帧
        for frame in frames:
            out.write(frame)
        out.release()

        # 合并音频
        temp_output = str(Path(output_path).with_suffix('.temp.mp4'))
        os.rename(output_path, temp_output)

        # 使用ffmpeg合并音视频
        os.system(f'ffmpeg -i {temp_output} -i {audio_path} -c:v copy -c:a aac {output_path}')
        os.remove(temp_output)

    def generate(self, video_path: str, audio_path: str, output_path: str):
        """生成唇形同步的视频"""
        try:
            # 1. 加载视频
            video_frames = self.load_video(video_path)
            logger.info(f"加载视频成功: {len(video_frames)} 帧")

            # 2. 提取音频特征
            mel_features = self.extract_audio_features(audio_path)
            logger.info(f"提取音频特征成功: shape={mel_features.shape}")

            # 3. 生成唇形同步的视频帧
            sync_frames = self.generate_sync_frames(video_frames, mel_features)
            logger.info(f"生成同步视频帧成功: {len(sync_frames)} 帧")

            # 4. 保存视频
            self.save_video(sync_frames, audio_path, output_path)
            logger.info(f"保存视频成功: {output_path}")

        except Exception as e:
            logger.error(f"生成唇形同步视频失败: {str(e)}")
            raise