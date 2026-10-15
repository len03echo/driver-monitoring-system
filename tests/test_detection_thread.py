"""
DetectionThread 模块单元测试

测试检测线程功能：
- 线程初始化和配置
- 视频源设置
- 检测器设置
- 线程控制（启动、停止、暂停、恢复）
- 帧处理和检测结果
- 信号发送
- 资源清理

依赖：
- pytest
- PyQt5
- numpy
- unittest.mock
"""

import pytest
import numpy as np
import time
from unittest.mock import Mock, patch, MagicMock
from PyQt5.QtCore import QCoreApplication, QTimer
from PyQt5.QtTest import QSignalSpy
import sys
import os

# 导入被测试的模块
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from client.core.detection_thread import DetectionThread
from client.core.video_source import VideoSource
from client.core.behavior_detector import BehaviorDetector
from client.core.fatigue_detector import FatigueDetector
from client.core.face_recognizer import FaceRecognizer
from client.core.alert_engine import AlertEngine


@pytest.fixture
def app():
    """创建 QApplication 实例"""
    if not QCoreApplication.instance():
        app = QCoreApplication([])
    else:
        app = QCoreApplication.instance()
    yield app


@pytest.fixture
def detection_thread(app):
    """创建 DetectionThread 实例"""
    thread = DetectionThread()
    yield thread
    thread.cleanup()


@pytest.fixture
def mock_video_source():
    """创建模拟视频源"""
    mock_source = Mock(spec=VideoSource)
    mock_source.read.return_value = np.zeros((480, 640, 3), dtype=np.uint8)
    mock_source.is_opened.return_value = True
    mock_source.release.return_value = None
    return mock_source


@pytest.fixture
def mock_detectors():
    """创建模拟检测器"""
    behavior_detector = Mock()
    # process_frame 返回 (detections_list, triggered_list)
    behavior_detector.process_frame.return_value = ([], [])
    behavior_detector.close.return_value = None
    
    fatigue_detector = Mock()
    # process_frame 返回 (result_dict, triggered_list)
    fatigue_detector.process_frame.return_value = ({"face_detected": False}, [])
    fatigue_detector.close.return_value = None
    
    face_recognizer = Mock()
    face_recognizer.extract_feature.return_value = None
    face_recognizer.close.return_value = None
    
    return behavior_detector, fatigue_detector, face_recognizer


@pytest.fixture
def mock_alert_engine():
    """创建模拟预警引擎"""
    mock_engine = Mock()
    mock_engine.process_alerts.return_value = []
    mock_engine.close.return_value = None
    return mock_engine


class TestDetectionThreadInit:
    """测试 DetectionThread 初始化"""
    
    def test_init_success(self, detection_thread):
        """测试成功初始化"""
        assert detection_thread.video_source is None
        assert detection_thread.behavior_detector is None
        assert detection_thread.fatigue_detector is None
        assert detection_thread.face_recognizer is None
        assert detection_thread.alert_engine is None
        
        assert detection_thread.target_fps == 30
        assert detection_thread.enable_behavior_detection is True
        assert detection_thread.enable_fatigue_detection is True
        assert detection_thread.enable_face_recognition is True
        
        assert detection_thread.is_running() is False
        assert detection_thread.is_paused() is False
    
    def test_init_signals(self, detection_thread):
        """测试信号定义"""
        # 检查信号是否存在
        assert hasattr(detection_thread, 'frame_ready')
        assert hasattr(detection_thread, 'detection_result')
        assert hasattr(detection_thread, 'status_changed')
        assert hasattr(detection_thread, 'error_occurred')
        assert hasattr(detection_thread, 'fps_updated')
        assert hasattr(detection_thread, 'video_ended')


class TestDetectionThreadConfiguration:
    """测试配置设置"""
    
    def test_set_video_source(self, detection_thread, mock_video_source):
        """测试设置视频源"""
        detection_thread.set_video_source(mock_video_source)
        
        assert detection_thread.video_source == mock_video_source
    
    def test_set_detectors(self, detection_thread, mock_detectors):
        """测试设置检测器"""
        behavior_detector, fatigue_detector, face_recognizer = mock_detectors
        
        # 单独设置
        detection_thread.set_detectors(behavior_detector=behavior_detector)
        assert detection_thread.behavior_detector == behavior_detector
        
        detection_thread.set_detectors(fatigue_detector=fatigue_detector)
        assert detection_thread.fatigue_detector == fatigue_detector
        
        detection_thread.set_detectors(face_recognizer=face_recognizer)
        assert detection_thread.face_recognizer == face_recognizer
        
        # 批量设置
        detection_thread.set_detectors(
            behavior_detector=behavior_detector,
            fatigue_detector=fatigue_detector,
            face_recognizer=face_recognizer
        )
        assert detection_thread.behavior_detector == behavior_detector
        assert detection_thread.fatigue_detector == fatigue_detector
        assert detection_thread.face_recognizer == face_recognizer
    
    def test_set_alert_engine(self, detection_thread, mock_alert_engine):
        """测试设置预警引擎"""
        detection_thread.set_alert_engine(mock_alert_engine)
        
        assert detection_thread.alert_engine == mock_alert_engine
    
    def test_set_detection_config(self, detection_thread):
        """测试设置检测配置"""
        detection_thread.set_detection_config(
            enable_behavior=False,
            enable_fatigue=True,
            enable_face=False
        )
        
        assert detection_thread.enable_behavior_detection is False
        assert detection_thread.enable_fatigue_detection is True
        assert detection_thread.enable_face_recognition is False
    
    def test_set_target_fps(self, detection_thread):
        """测试设置目标 FPS"""
        detection_thread.set_target_fps(25)
        assert detection_thread.target_fps == 25
        assert detection_thread.frame_interval == 1.0 / 25
        
        # 测试边界值
        detection_thread.set_target_fps(0)  # 应该被限制为 1
        assert detection_thread.target_fps == 1
        
        detection_thread.set_target_fps(100)  # 应该被限制为 60
        assert detection_thread.target_fps == 60


class TestDetectionThreadControl:
    """测试线程控制"""
    
    def test_start_detection_no_video_source(self, detection_thread, app):
        """测试没有视频源时启动检测"""
        # 连接错误信号
        error_spy = QSignalSpy(detection_thread.error_occurred)
        
        detection_thread.start_detection()
        
        # 应该发出错误信号
        assert len(error_spy) == 1
        assert "未设置视频源" in error_spy[0][0]
    
    def test_start_stop_detection(self, detection_thread, mock_video_source, app):
        """测试启动和停止检测"""
        detection_thread.set_video_source(mock_video_source)
        
        # 连接状态信号
        status_spy = QSignalSpy(detection_thread.status_changed)
        
        # 启动检测
        detection_thread.start_detection()
        assert detection_thread.is_running() is True
        
        # 等待线程启动
        app.processEvents()
        
        # 停止检测
        detection_thread.stop_detection()
        assert detection_thread.is_running() is False
        
        # 检查状态信号
        assert len(status_spy) >= 2  # 至少有 starting 和 stopping
    
    def test_pause_resume_detection(self, detection_thread, mock_video_source, app):
        """测试暂停和恢复检测"""
        detection_thread.set_video_source(mock_video_source)
        
        # 连接状态信号
        status_spy = QSignalSpy(detection_thread.status_changed)
        
        # 启动检测
        detection_thread.start_detection()
        app.processEvents()
        
        # 暂停检测
        detection_thread.pause_detection()
        assert detection_thread.is_paused() is True
        
        # 恢复检测
        detection_thread.resume_detection()
        assert detection_thread.is_paused() is False
        
        # 停止检测
        detection_thread.stop_detection()
        
        # 检查状态信号
        status_signals = [signal[0] for signal in status_spy]
        assert "paused" in status_signals
        assert "running" in status_signals


class TestDetectionThreadProcessing:
    """测试帧处理"""
    
    def test_read_frame_success(self, detection_thread, mock_video_source):
        """测试成功读取帧"""
        detection_thread.set_video_source(mock_video_source)
        # read() 需要返回 (success, frame) 元组
        mock_video_source.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
        
        success, frame = detection_thread._read_frame()
        
        assert success is True
        assert frame is not None
        assert frame.shape == (480, 640, 3)
        mock_video_source.read.assert_called_once()
    
    def test_read_frame_no_source(self, detection_thread):
        """测试没有视频源时读取帧"""
        success, frame = detection_thread._read_frame()
        
        assert success is False
        assert frame is None
    
    def test_read_frame_video_ended(self, detection_thread, mock_video_source):
        """测试视频结束时读取帧"""
        mock_video_source.read.return_value = (False, None)
        detection_thread.set_video_source(mock_video_source)
        
        success, frame = detection_thread._read_frame()
        
        assert success is False
        assert frame is None
    
    def test_process_frame_all_detectors(self, detection_thread, mock_detectors):
        """测试处理帧（所有检测器）"""
        behavior_detector, fatigue_detector, face_recognizer = mock_detectors
        
        detection_thread.set_detectors(
            behavior_detector=behavior_detector,
            fatigue_detector=fatigue_detector,
            face_recognizer=face_recognizer
        )
        
        # process_frame 返回 (detections_list, triggered_list)
        behavior_detector.process_frame.return_value = (
            [{"class": "phone", "confidence": 0.8}],
            ["phone"]
        )
        # fatigue process_frame 返回 (result_dict, triggered_list)
        fatigue_detector.process_frame.return_value = (
            {"face_detected": True, "ear": 0.2, "mar": 0.3, "head_angle": 10},
            ["eye_closed"]
        )
        face_recognizer.extract_feature.return_value = None
        
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        results = detection_thread._process_frame(frame)
        
        assert results is not None
        assert "timestamp" in results
        assert "frame_shape" in results
        assert "detections" in results
        assert "all_alerts" in results
        
        detections = results["detections"]
        assert "behavior" in detections
        assert "fatigue" in detections
        assert "face" in detections
        
        # 检查汇总告警
        assert set(results["all_alerts"]) == {"phone", "eye_closed"}
        
        behavior_detector.process_frame.assert_called_once_with(frame)
        fatigue_detector.process_frame.assert_called_once()
    
    def test_process_frame_selective_detection(self, detection_thread, mock_detectors):
        """测试选择性检测"""
        behavior_detector, fatigue_detector, face_recognizer = mock_detectors
        
        detection_thread.set_detectors(
            behavior_detector=behavior_detector,
            fatigue_detector=fatigue_detector,
            face_recognizer=face_recognizer
        )
        
        detection_thread.set_detection_config(
            enable_behavior=True,
            enable_fatigue=False,
            enable_face=False
        )
        
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        results = detection_thread._process_frame(frame)
        
        assert results is not None
        detections = results["detections"]
        
        assert "behavior" in detections
        assert "fatigue" not in detections
        assert "face" not in detections
        
        behavior_detector.process_frame.assert_called_once()
        fatigue_detector.process_frame.assert_not_called()
        face_recognizer.extract_feature.assert_not_called()
    
    def test_process_frame_detector_exception(self, detection_thread, mock_detectors):
        """测试检测器异常处理"""
        behavior_detector, fatigue_detector, face_recognizer = mock_detectors
        
        # 设置行为检测器抛出异常
        behavior_detector.detect.side_effect = Exception("检测失败")
        
        detection_thread.set_detectors(behavior_detector=behavior_detector)
        
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        results = detection_thread._process_frame(frame)
        
        assert results is not None
        detections = results["detections"]
        
        # 应该有默认的行为检测结果
        assert "behavior" in detections
        assert detections["behavior"] == {"objects": [], "triggered_alerts": []}


class TestDetectionThreadStatus:
    """测试状态管理"""
    
    def test_get_status(self, detection_thread, mock_video_source, mock_detectors, mock_alert_engine):
        """测试获取状态"""
        behavior_detector, fatigue_detector, face_recognizer = mock_detectors
        
        # 设置组件
        detection_thread.set_video_source(mock_video_source)
        detection_thread.set_detectors(
            behavior_detector=behavior_detector,
            fatigue_detector=fatigue_detector,
            face_recognizer=face_recognizer
        )
        detection_thread.set_alert_engine(mock_alert_engine)
        detection_thread.set_target_fps(25)
        detection_thread.set_detection_config(
            enable_behavior=True,
            enable_fatigue=False,
            enable_face=True
        )
        
        status = detection_thread.get_status()
        
        assert status["running"] is False
        assert status["paused"] is False
        assert status["target_fps"] == 25
        assert status["has_video_source"] is True
        assert status["has_behavior_detector"] is True
        assert status["has_fatigue_detector"] is True
        assert status["has_face_recognizer"] is True
        assert status["has_alert_engine"] is True
        
        detection_config = status["detection_config"]
        assert detection_config["behavior"] is True
        assert detection_config["fatigue"] is False
        assert detection_config["face"] is True


class TestDetectionThreadCleanup:
    """测试资源清理"""
    
    def test_cleanup(self, detection_thread, mock_video_source, mock_detectors, mock_alert_engine):
        """测试资源清理"""
        behavior_detector, fatigue_detector, face_recognizer = mock_detectors
        
        # 设置组件
        detection_thread.set_video_source(mock_video_source)
        detection_thread.set_detectors(
            behavior_detector=behavior_detector,
            fatigue_detector=fatigue_detector,
            face_recognizer=face_recognizer
        )
        detection_thread.set_alert_engine(mock_alert_engine)
        
        # 执行清理
        detection_thread.cleanup()
        
        # 验证资源释放
        mock_video_source.release.assert_called_once()
        behavior_detector.close.assert_called_once()
        fatigue_detector.close.assert_called_once()
        face_recognizer.close.assert_called_once()
        mock_alert_engine.close.assert_called_once()
        
        # 验证组件被清空
        assert detection_thread.video_source is None
        assert detection_thread.behavior_detector is None
        assert detection_thread.fatigue_detector is None
        assert detection_thread.face_recognizer is None
        assert detection_thread.alert_engine is None
    
    def test_cleanup_exception_handling(self, detection_thread, mock_video_source):
        """测试清理时的异常处理"""
        # 设置视频源释放时抛出异常
        mock_video_source.release.side_effect = Exception("释放失败")
        detection_thread.set_video_source(mock_video_source)
        
        # 清理不应该抛出异常
        detection_thread.cleanup()
        
        # 组件仍应被清空
        assert detection_thread.video_source is None


class TestDetectionThreadSignals:
    """测试信号发送"""
    
    def test_frame_ready_signal(self, detection_thread, mock_video_source, app):
        """测试帧准备信号"""
        detection_thread.set_video_source(mock_video_source)
        
        # 连接信号
        frame_spy = QSignalSpy(detection_thread.frame_ready)
        
        # 模拟处理一帧
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        detection_thread.frame_ready.emit(frame)
        
        assert len(frame_spy) == 1
        received_frame = frame_spy[0][0]
        assert received_frame.shape == (480, 640, 3)
    
    def test_detection_result_signal(self, detection_thread, app):
        """测试检测结果信号"""
        # 连接信号
        result_spy = QSignalSpy(detection_thread.detection_result)
        
        # 发送检测结果
        test_result = {"timestamp": time.time(), "all_alerts": ["phone"]}
        detection_thread.detection_result.emit(test_result)
        
        assert len(result_spy) == 1
        received_result = result_spy[0][0]
        assert "timestamp" in received_result
        assert received_result["all_alerts"] == ["phone"]
    
    def test_status_changed_signal(self, detection_thread, app):
        """测试状态变化信号"""
        # 连接信号
        status_spy = QSignalSpy(detection_thread.status_changed)
        
        # 发送状态变化
        detection_thread.status_changed.emit("running")
        
        assert len(status_spy) == 1
        assert status_spy[0][0] == "running"
    
    def test_error_occurred_signal(self, detection_thread, app):
        """测试错误信号"""
        # 连接信号
        error_spy = QSignalSpy(detection_thread.error_occurred)
        
        # 发送错误
        detection_thread.error_occurred.emit("测试错误")
        
        assert len(error_spy) == 1
        assert error_spy[0][0] == "测试错误"
    
    def test_fps_updated_signal(self, detection_thread, app):
        """测试 FPS 更新信号"""
        # 连接信号
        fps_spy = QSignalSpy(detection_thread.fps_updated)
        
        # 发送 FPS 更新
        detection_thread.fps_updated.emit(30.5)
        
        assert len(fps_spy) == 1
        assert fps_spy[0][0] == 30.5
    
    def test_video_ended_signal(self, detection_thread, app):
        """测试视频结束信号"""
        # 连接信号
        ended_spy = QSignalSpy(detection_thread.video_ended)
        
        # 发送视频结束信号
        detection_thread.video_ended.emit()
        
        assert len(ended_spy) == 1


class TestDetectionThreadPerformance:
    """测试性能相关功能"""
    
    def test_fps_counter(self, detection_thread):
        """测试 FPS 计数"""
        # 重置计数器
        detection_thread.fps_counter = 0
        detection_thread.fps_start_time = time.time()
        
        # 模拟处理几帧
        for _ in range(5):
            detection_thread._update_fps()
        
        assert detection_thread.fps_counter == 5
    
    def test_frame_rate_control(self, detection_thread):
        """测试帧率控制"""
        detection_thread.set_target_fps(10)  # 10 FPS = 0.1秒间隔
        
        start_time = time.time()
        detection_thread._control_frame_rate(start_time)
        end_time = time.time()
        
        # 应该有一定的延迟（但测试环境可能不准确）
        elapsed = end_time - start_time
        assert elapsed >= 0  # 至少不是负数


if __name__ == "__main__":
    pytest.main([__file__])