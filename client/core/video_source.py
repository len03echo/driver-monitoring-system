"""
视频输入源模块

提供统一的视频帧读取接口，支持摄像头和视频文件两种输入源。
包含 VideoSource 抽象基类、CameraSource 和 VideoFileSource 实现类，
以及 VideoSourceFactory 工厂方法。

依赖：
- opencv-python (cv2)
- numpy
"""

from abc import ABC, abstractmethod
import os
import cv2
import numpy as np
from typing import Optional, Tuple


class VideoSource(ABC):
    """
    视频输入源抽象基类。
    所有具体输入源（摄像头、视频文件）均继承此类，
    DetectionThread 仅依赖此接口，不感知具体实现。
    """

    @abstractmethod
    def open(self) -> bool:
        """
        打开视频源。
        :return: 打开成功返回 True，失败返回 False
        """
        pass

    @abstractmethod
    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        """
        读取下一帧。
        :return: (success, frame)
                 success=True 且 frame 非 None：正常读取
                 success=False：读取失败（摄像头断开或文件结束）
        """
        pass

    @abstractmethod
    def is_opened(self) -> bool:
        """返回视频源是否处于打开状态。"""
        pass

    @abstractmethod
    def release(self) -> None:
        """释放视频源资源。"""
        pass

    @property
    @abstractmethod
    def source_type(self) -> str:
        """返回输入源类型标识：'camera' 或 'video_file'。"""
        pass


class CameraSource(VideoSource):
    """
    实时摄像头输入源。
    封装 cv2.VideoCapture(device_index)。
    """

    def __init__(self, device_index: int = 0) -> None:
        """
        :param device_index: 摄像头设备索引，默认 0（第一个摄像头）
        """
        self._cap: Optional[cv2.VideoCapture] = None
        self._device_index = device_index

    def open(self) -> bool:
        """
        打开摄像头设备。
        :return: 打开成功返回 True，失败返回 False
        """
        try:
            self._cap = cv2.VideoCapture(self._device_index)
            if not self._cap.isOpened():
                self._cap = None
                return False
            
            # 设置缓冲区大小为1，减少延迟
            self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            # 测试读取一帧以确保摄像头正常工作
            ret, frame = self._cap.read()
            if not ret or frame is None:
                self._cap.release()
                self._cap = None
                return False
                
            return True
        except Exception:
            if self._cap is not None:
                self._cap.release()
                self._cap = None
            return False

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        """
        读取下一帧。
        :return: (success, frame)
        """
        if self._cap is None or not self._cap.isOpened():
            return False, None
        
        try:
            ret, frame = self._cap.read()
            if ret and frame is not None:
                return True, frame
            else:
                return False, None
        except Exception:
            return False, None

    def is_opened(self) -> bool:
        """返回摄像头是否处于打开状态。"""
        return self._cap is not None and self._cap.isOpened()

    def release(self) -> None:
        """释放摄像头资源。"""
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    @property
    def source_type(self) -> str:
        return "camera"

    def get_fps(self) -> float:
        """获取摄像头帧率。"""
        if self._cap is not None and self._cap.isOpened():
            return self._cap.get(cv2.CAP_PROP_FPS)
        return 0.0

    def get_resolution(self) -> Tuple[int, int]:
        """获取摄像头分辨率 (width, height)。"""
        if self._cap is not None and self._cap.isOpened():
            width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            return width, height
        return 0, 0


class VideoFileSource(VideoSource):
    """
    本地视频文件输入源。
    封装 cv2.VideoCapture(file_path)。
    当 read() 返回 success=False 时，表示文件已播放至结尾。
    """

    def __init__(self, file_path: str) -> None:
        """
        :param file_path: 视频文件绝对路径或相对路径
        """
        self._cap: Optional[cv2.VideoCapture] = None
        self._file_path = file_path

    def open(self) -> bool:
        """
        打开视频文件。
        :return: 打开成功返回 True，失败返回 False
        """
        # 检查文件是否存在
        if not os.path.exists(self._file_path):
            return False
        
        try:
            self._cap = cv2.VideoCapture(self._file_path)
            if not self._cap.isOpened():
                self._cap = None
                return False
            
            # 测试读取一帧以确保文件格式正确
            ret, frame = self._cap.read()
            if not ret or frame is None:
                self._cap.release()
                self._cap = None
                return False
            
            # 重置到文件开头
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            return True
        except Exception:
            if self._cap is not None:
                self._cap.release()
                self._cap = None
            return False

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        """
        读取下一帧。
        :return: (success, frame)
        """
        if self._cap is None or not self._cap.isOpened():
            return False, None
        
        try:
            ret, frame = self._cap.read()
            if ret and frame is not None:
                return True, frame
            else:
                # 文件播放结束
                return False, None
        except Exception:
            return False, None

    def is_opened(self) -> bool:
        """返回视频文件是否处于打开状态。"""
        return self._cap is not None and self._cap.isOpened()

    def release(self) -> None:
        """释放视频文件资源。"""
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    @property
    def source_type(self) -> str:
        return "video_file"

    def get_fps(self) -> float:
        """获取视频文件帧率。"""
        if self._cap is not None and self._cap.isOpened():
            return self._cap.get(cv2.CAP_PROP_FPS)
        return 0.0

    def get_frame_count(self) -> int:
        """获取视频文件总帧数。"""
        if self._cap is not None and self._cap.isOpened():
            return int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))
        return 0

    def get_duration(self) -> float:
        """获取视频文件时长（秒）。"""
        fps = self.get_fps()
        frame_count = self.get_frame_count()
        if fps > 0:
            return frame_count / fps
        return 0.0

    def get_current_position(self) -> int:
        """获取当前播放位置（帧索引）。"""
        if self._cap is not None and self._cap.isOpened():
            return int(self._cap.get(cv2.CAP_PROP_POS_FRAMES))
        return 0

    def seek_to_frame(self, frame_index: int) -> bool:
        """
        跳转到指定帧。
        :param frame_index: 目标帧索引
        :return: 跳转成功返回 True
        """
        if self._cap is not None and self._cap.isOpened():
            try:
                self._cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
                return True
            except Exception:
                return False
        return False

    def get_resolution(self) -> Tuple[int, int]:
        """获取视频文件分辨率 (width, height)。"""
        if self._cap is not None and self._cap.isOpened():
            width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            return width, height
        return 0, 0


class VideoSourceFactory:
    """
    视频输入源工厂，根据配置创建对应的 VideoSource 实例。
    """

    @staticmethod
    def create(source_type: str, **kwargs) -> VideoSource:
        """
        创建视频输入源实例。
        
        :param source_type: "camera" 或 "video_file"
        :param kwargs:
            - camera: device_index (int, 默认 0)
            - video_file: file_path (str, 必填)
        :return: 对应的 VideoSource 实例
        :raises ValueError: source_type 不合法时抛出
        """
        if source_type == "camera":
            device_index = kwargs.get("device_index", 0)
            return CameraSource(device_index=device_index)
        elif source_type == "video_file":
            if "file_path" not in kwargs:
                raise ValueError("创建 VideoFileSource 时必须提供 file_path 参数")
            file_path = kwargs["file_path"]
            return VideoFileSource(file_path=file_path)
        else:
            raise ValueError(f"不支持的视频输入源类型：{source_type}")

    @staticmethod
    def create_camera(device_index: int = 0) -> CameraSource:
        """
        创建摄像头输入源的便捷方法。
        
        :param device_index: 摄像头设备索引，默认 0
        :return: CameraSource 实例
        """
        return CameraSource(device_index=device_index)

    @staticmethod
    def create_video_file(file_path: str) -> VideoFileSource:
        """
        创建视频文件输入源的便捷方法。
        
        :param file_path: 视频文件路径
        :return: VideoFileSource 实例
        """
        return VideoFileSource(file_path=file_path)