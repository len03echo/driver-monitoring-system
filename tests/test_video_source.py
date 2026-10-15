"""
VideoSource 模块单元测试

测试 VideoSource 抽象基类及其实现类的功能：
- CameraSource：摄像头输入源
- VideoFileSource：视频文件输入源  
- VideoSourceFactory：工厂方法

依赖：
- pytest
- opencv-python
- numpy
"""

import pytest
import numpy as np
import cv2
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock

# 导入被测试的模块
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from client.core.video_source import (
    VideoSource, 
    CameraSource, 
    VideoFileSource, 
    VideoSourceFactory
)


class TestVideoSource:
    """测试 VideoSource 抽象基类"""
    
    def test_abstract_class_cannot_be_instantiated(self):
        """测试抽象基类不能直接实例化"""
        with pytest.raises(TypeError):
            VideoSource()


class TestCameraSource:
    """测试 CameraSource 摄像头输入源"""
    
    def test_init_default_device_index(self):
        """测试默认设备索引初始化"""
        camera = CameraSource()
        assert camera._device_index == 0
        assert camera.source_type == "camera"
    
    def test_init_custom_device_index(self):
        """测试自定义设备索引初始化"""
        camera = CameraSource(device_index=1)
        assert camera._device_index == 1
        assert camera.source_type == "camera"
    
    @patch('cv2.VideoCapture')
    def test_open_success(self, mock_video_capture):
        """测试成功打开摄像头"""
        # 模拟成功的摄像头
        mock_cap = Mock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
        mock_video_capture.return_value = mock_cap
        
        camera = CameraSource(device_index=0)
        result = camera.open()
        
        assert result is True
        assert camera.is_opened() is True
        mock_video_capture.assert_called_once_with(0)
        mock_cap.set.assert_called_once_with(cv2.CAP_PROP_BUFFERSIZE, 1)
    
    @patch('cv2.VideoCapture')
    def test_open_failure_device_not_available(self, mock_video_capture):
        """测试摄像头设备不可用"""
        # 模拟摄像头打开失败
        mock_cap = Mock()
        mock_cap.isOpened.return_value = False
        mock_video_capture.return_value = mock_cap
        
        camera = CameraSource(device_index=0)
        result = camera.open()
        
        assert result is False
        assert camera.is_opened() is False
    
    @patch('cv2.VideoCapture')
    def test_open_failure_cannot_read_frame(self, mock_video_capture):
        """测试摄像头无法读取帧"""
        # 模拟摄像头打开成功但无法读取帧
        mock_cap = Mock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (False, None)
        mock_video_capture.return_value = mock_cap
        
        camera = CameraSource(device_index=0)
        result = camera.open()
        
        assert result is False
        assert camera.is_opened() is False
        mock_cap.release.assert_called_once()
    
    @patch('cv2.VideoCapture')
    def test_open_exception_handling(self, mock_video_capture):
        """测试打开摄像头时的异常处理"""
        # 模拟异常
        mock_video_capture.side_effect = Exception("摄像头初始化失败")
        
        camera = CameraSource(device_index=0)
        result = camera.open()
        
        assert result is False
        assert camera.is_opened() is False
    
    def test_read_without_opening(self):
        """测试未打开摄像头时读取帧"""
        camera = CameraSource()
        success, frame = camera.read()
        
        assert success is False
        assert frame is None
    
    @patch('cv2.VideoCapture')
    def test_read_success(self, mock_video_capture):
        """测试成功读取帧"""
        # 模拟成功读取
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        mock_cap = Mock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, test_frame)
        mock_video_capture.return_value = mock_cap
        
        camera = CameraSource()
        camera.open()
        success, frame = camera.read()
        
        assert success is True
        assert frame is not None
        assert isinstance(frame, np.ndarray)
        assert frame.shape == (480, 640, 3)
    
    @patch('cv2.VideoCapture')
    def test_read_failure(self, mock_video_capture):
        """测试读取帧失败"""
        # 模拟读取失败
        mock_cap = Mock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.side_effect = [(True, np.zeros((480, 640, 3), dtype=np.uint8)), (False, None)]
        mock_video_capture.return_value = mock_cap
        
        camera = CameraSource()
        camera.open()
        
        # 第二次读取失败
        success, frame = camera.read()
        assert success is False
        assert frame is None
    
    @patch('cv2.VideoCapture')
    def test_read_exception_handling(self, mock_video_capture):
        """测试读取帧时的异常处理"""
        mock_cap = Mock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.side_effect = [
            (True, np.zeros((480, 640, 3), dtype=np.uint8)),  # 初始化时成功
            Exception("读取失败")  # 实际读取时异常
        ]
        mock_video_capture.return_value = mock_cap
        
        camera = CameraSource()
        camera.open()
        success, frame = camera.read()
        
        assert success is False
        assert frame is None
    
    @patch('cv2.VideoCapture')
    def test_release(self, mock_video_capture):
        """测试释放摄像头资源"""
        mock_cap = Mock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
        mock_video_capture.return_value = mock_cap
        
        camera = CameraSource()
        camera.open()
        camera.release()
        
        mock_cap.release.assert_called()
        assert camera.is_opened() is False
    
    @patch('cv2.VideoCapture')
    def test_get_fps(self, mock_video_capture):
        """测试获取帧率"""
        mock_cap = Mock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
        mock_cap.get.return_value = 30.0
        mock_video_capture.return_value = mock_cap
        
        camera = CameraSource()
        camera.open()
        fps = camera.get_fps()
        
        assert fps == 30.0
        mock_cap.get.assert_called_with(cv2.CAP_PROP_FPS)
    
    @patch('cv2.VideoCapture')
    def test_get_resolution(self, mock_video_capture):
        """测试获取分辨率"""
        mock_cap = Mock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
        mock_cap.get.side_effect = lambda prop: {
            cv2.CAP_PROP_FRAME_WIDTH: 640,
            cv2.CAP_PROP_FRAME_HEIGHT: 480
        }[prop]
        mock_video_capture.return_value = mock_cap
        
        camera = CameraSource()
        camera.open()
        width, height = camera.get_resolution()
        
        assert width == 640
        assert height == 480


class TestVideoFileSource:
    """测试 VideoFileSource 视频文件输入源"""
    
    def test_init(self):
        """测试初始化"""
        video_file = VideoFileSource("test.mp4")
        assert video_file._file_path == "test.mp4"
        assert video_file.source_type == "video_file"
    
    def test_open_file_not_exists(self):
        """测试打开不存在的文件"""
        video_file = VideoFileSource("nonexistent.mp4")
        result = video_file.open()
        
        assert result is False
        assert video_file.is_opened() is False
    
    @patch('os.path.exists')
    @patch('cv2.VideoCapture')
    def test_open_success(self, mock_video_capture, mock_exists):
        """测试成功打开视频文件"""
        # 模拟文件存在
        mock_exists.return_value = True
        
        # 模拟成功的视频文件
        mock_cap = Mock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
        mock_video_capture.return_value = mock_cap
        
        video_file = VideoFileSource("test.mp4")
        result = video_file.open()
        
        assert result is True
        assert video_file.is_opened() is True
        mock_video_capture.assert_called_once_with("test.mp4")
        # 验证重置到文件开头
        mock_cap.set.assert_called_once_with(cv2.CAP_PROP_POS_FRAMES, 0)
    
    @patch('os.path.exists')
    @patch('cv2.VideoCapture')
    def test_open_failure_cannot_open(self, mock_video_capture, mock_exists):
        """测试无法打开视频文件"""
        mock_exists.return_value = True
        
        # 模拟文件无法打开
        mock_cap = Mock()
        mock_cap.isOpened.return_value = False
        mock_video_capture.return_value = mock_cap
        
        video_file = VideoFileSource("test.mp4")
        result = video_file.open()
        
        assert result is False
        assert video_file.is_opened() is False
    
    @patch('os.path.exists')
    @patch('cv2.VideoCapture')
    def test_open_failure_cannot_read_frame(self, mock_video_capture, mock_exists):
        """测试视频文件无法读取帧"""
        mock_exists.return_value = True
        
        # 模拟文件打开成功但无法读取帧
        mock_cap = Mock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (False, None)
        mock_video_capture.return_value = mock_cap
        
        video_file = VideoFileSource("test.mp4")
        result = video_file.open()
        
        assert result is False
        assert video_file.is_opened() is False
        mock_cap.release.assert_called_once()
    
    @patch('os.path.exists')
    @patch('cv2.VideoCapture')
    def test_open_exception_handling(self, mock_video_capture, mock_exists):
        """测试打开视频文件时的异常处理"""
        mock_exists.return_value = True
        mock_video_capture.side_effect = Exception("文件格式不支持")
        
        video_file = VideoFileSource("test.mp4")
        result = video_file.open()
        
        assert result is False
        assert video_file.is_opened() is False
    
    def test_read_without_opening(self):
        """测试未打开文件时读取帧"""
        video_file = VideoFileSource("test.mp4")
        success, frame = video_file.read()
        
        assert success is False
        assert frame is None
    
    @patch('os.path.exists')
    @patch('cv2.VideoCapture')
    def test_read_success(self, mock_video_capture, mock_exists):
        """测试成功读取帧"""
        mock_exists.return_value = True
        
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        mock_cap = Mock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.side_effect = [
            (True, test_frame),  # 初始化时
            (True, test_frame)   # 实际读取时
        ]
        mock_video_capture.return_value = mock_cap
        
        video_file = VideoFileSource("test.mp4")
        video_file.open()
        success, frame = video_file.read()
        
        assert success is True
        assert frame is not None
        assert isinstance(frame, np.ndarray)
    
    @patch('os.path.exists')
    @patch('cv2.VideoCapture')
    def test_read_end_of_file(self, mock_video_capture, mock_exists):
        """测试读取到文件结尾"""
        mock_exists.return_value = True
        
        mock_cap = Mock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.side_effect = [
            (True, np.zeros((480, 640, 3), dtype=np.uint8)),  # 初始化时
            (False, None)  # 文件结束
        ]
        mock_video_capture.return_value = mock_cap
        
        video_file = VideoFileSource("test.mp4")
        video_file.open()
        success, frame = video_file.read()
        
        assert success is False
        assert frame is None
    
    @patch('os.path.exists')
    @patch('cv2.VideoCapture')
    def test_get_frame_count(self, mock_video_capture, mock_exists):
        """测试获取总帧数"""
        mock_exists.return_value = True
        
        mock_cap = Mock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
        mock_cap.get.return_value = 1000
        mock_video_capture.return_value = mock_cap
        
        video_file = VideoFileSource("test.mp4")
        video_file.open()
        frame_count = video_file.get_frame_count()
        
        assert frame_count == 1000
        mock_cap.get.assert_called_with(cv2.CAP_PROP_FRAME_COUNT)
    
    @patch('os.path.exists')
    @patch('cv2.VideoCapture')
    def test_get_duration(self, mock_video_capture, mock_exists):
        """测试获取视频时长"""
        mock_exists.return_value = True
        
        mock_cap = Mock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
        mock_cap.get.side_effect = lambda prop: {
            cv2.CAP_PROP_FPS: 30.0,
            cv2.CAP_PROP_FRAME_COUNT: 900
        }[prop]
        mock_video_capture.return_value = mock_cap
        
        video_file = VideoFileSource("test.mp4")
        video_file.open()
        duration = video_file.get_duration()
        
        assert duration == 30.0  # 900 frames / 30 fps = 30 seconds
    
    @patch('os.path.exists')
    @patch('cv2.VideoCapture')
    def test_seek_to_frame(self, mock_video_capture, mock_exists):
        """测试跳转到指定帧"""
        mock_exists.return_value = True
        
        mock_cap = Mock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
        mock_video_capture.return_value = mock_cap
        
        video_file = VideoFileSource("test.mp4")
        video_file.open()
        result = video_file.seek_to_frame(100)
        
        assert result is True
        mock_cap.set.assert_called_with(cv2.CAP_PROP_POS_FRAMES, 100)
    
    @patch('os.path.exists')
    @patch('cv2.VideoCapture')
    def test_release(self, mock_video_capture, mock_exists):
        """测试释放视频文件资源"""
        mock_exists.return_value = True
        
        mock_cap = Mock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
        mock_video_capture.return_value = mock_cap
        
        video_file = VideoFileSource("test.mp4")
        video_file.open()
        video_file.release()
        
        mock_cap.release.assert_called()
        assert video_file.is_opened() is False


class TestVideoSourceFactory:
    """测试 VideoSourceFactory 工厂方法"""
    
    def test_create_camera_default(self):
        """测试创建默认摄像头源"""
        source = VideoSourceFactory.create("camera")
        
        assert isinstance(source, CameraSource)
        assert source._device_index == 0
        assert source.source_type == "camera"
    
    def test_create_camera_custom_device(self):
        """测试创建自定义设备索引的摄像头源"""
        source = VideoSourceFactory.create("camera", device_index=1)
        
        assert isinstance(source, CameraSource)
        assert source._device_index == 1
        assert source.source_type == "camera"
    
    def test_create_video_file(self):
        """测试创建视频文件源"""
        source = VideoSourceFactory.create("video_file", file_path="test.mp4")
        
        assert isinstance(source, VideoFileSource)
        assert source._file_path == "test.mp4"
        assert source.source_type == "video_file"
    
    def test_create_video_file_missing_path(self):
        """测试创建视频文件源时缺少文件路径"""
        with pytest.raises(ValueError, match="创建 VideoFileSource 时必须提供 file_path 参数"):
            VideoSourceFactory.create("video_file")
    
    def test_create_invalid_source_type(self):
        """测试创建无效的输入源类型"""
        with pytest.raises(ValueError, match="不支持的视频输入源类型：invalid"):
            VideoSourceFactory.create("invalid")
    
    def test_create_camera_convenience_method(self):
        """测试摄像头便捷创建方法"""
        source = VideoSourceFactory.create_camera()
        
        assert isinstance(source, CameraSource)
        assert source._device_index == 0
        
        source2 = VideoSourceFactory.create_camera(device_index=2)
        assert source2._device_index == 2
    
    def test_create_video_file_convenience_method(self):
        """测试视频文件便捷创建方法"""
        source = VideoSourceFactory.create_video_file("test.mp4")
        
        assert isinstance(source, VideoFileSource)
        assert source._file_path == "test.mp4"


class TestIntegration:
    """集成测试"""
    
    def test_camera_source_lifecycle(self):
        """测试摄像头源的完整生命周期"""
        camera = CameraSource(device_index=0)
        
        # 初始状态
        assert not camera.is_opened()
        assert camera.source_type == "camera"
        
        # 尝试在未打开时读取
        success, frame = camera.read()
        assert not success
        assert frame is None
        
        # 释放未打开的资源应该安全
        camera.release()
        assert not camera.is_opened()
    
    def test_video_file_source_lifecycle(self):
        """测试视频文件源的完整生命周期"""
        video_file = VideoFileSource("nonexistent.mp4")
        
        # 初始状态
        assert not video_file.is_opened()
        assert video_file.source_type == "video_file"
        
        # 尝试打开不存在的文件
        result = video_file.open()
        assert not result
        assert not video_file.is_opened()
        
        # 尝试在未打开时读取
        success, frame = video_file.read()
        assert not success
        assert frame is None
        
        # 释放未打开的资源应该安全
        video_file.release()
        assert not video_file.is_opened()
    
    def test_factory_creates_correct_types(self):
        """测试工厂方法创建正确的类型"""
        # 测试所有创建方法返回的都是 VideoSource 的子类
        camera1 = VideoSourceFactory.create("camera")
        camera2 = VideoSourceFactory.create_camera()
        video1 = VideoSourceFactory.create("video_file", file_path="test.mp4")
        video2 = VideoSourceFactory.create_video_file("test.mp4")
        
        assert isinstance(camera1, VideoSource)
        assert isinstance(camera2, VideoSource)
        assert isinstance(video1, VideoSource)
        assert isinstance(video2, VideoSource)
        
        assert camera1.source_type == "camera"
        assert camera2.source_type == "camera"
        assert video1.source_type == "video_file"
        assert video2.source_type == "video_file"


if __name__ == "__main__":
    pytest.main([__file__])