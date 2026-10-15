"""
BehaviorDetector 模块单元测试

测试基于 YOLOv8 的危险行为检测器功能：
- 模型加载和初始化
- 目标检测功能
- 连续帧计数逻辑
- 告警触发机制
- 错误处理

依赖：
- pytest
- numpy
- unittest.mock
"""

import pytest
import numpy as np
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict

# 导入被测试的模块
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from client.core.behavior_detector import BehaviorDetector


class TestBehaviorDetectorInit:
    """测试 BehaviorDetector 初始化"""
    
    @patch('client.core.behavior_detector.YOLO')
    @patch('os.path.exists')
    def test_init_success(self, mock_exists, mock_yolo):
        """测试成功初始化"""
        mock_exists.return_value = True
        mock_model = Mock()
        mock_yolo.return_value = mock_model
        
        detector = BehaviorDetector("test_model.pt", consecutive_threshold=5)
        
        assert detector.model_path == "test_model.pt"
        assert detector.consecutive_threshold == 5
        assert detector.model == mock_model
        # 实际代码类别：smoke / phone / drink
        assert detector.frame_counters == {"smoke": 0, "phone": 0, "drink": 0}
        mock_yolo.assert_called_once_with("test_model.pt")
    
    @patch('os.path.exists')
    def test_init_model_file_not_exists(self, mock_exists):
        """测试模型文件不存在（含路径分隔符才触发 FileNotFoundError）"""
        mock_exists.return_value = False
        
        with pytest.raises(FileNotFoundError, match="YOLOv8 模型文件不存在"):
            # 带路径分隔符，确保走本地路径检查分支
            BehaviorDetector("path/to/nonexistent.pt")
    
    @patch('client.core.behavior_detector.YOLO')
    @patch('os.path.exists')
    def test_init_model_load_failure(self, mock_exists, mock_yolo):
        """测试模型加载失败"""
        mock_exists.return_value = True
        mock_yolo.side_effect = Exception("模型加载错误")
        
        with pytest.raises(RuntimeError, match="YOLOv8 模型加载失败"):
            BehaviorDetector("test_model.pt")
    
    @patch('client.core.behavior_detector.YOLO')
    @patch('os.path.exists')
    def test_init_default_threshold(self, mock_exists, mock_yolo):
        """测试默认连续帧阈值"""
        mock_exists.return_value = True
        mock_yolo.return_value = Mock()
        
        detector = BehaviorDetector("test_model.pt")
        
        assert detector.consecutive_threshold == 10


class TestBehaviorDetectorDetect:
    """测试目标检测功能"""
    
    def setup_method(self):
        """设置测试环境"""
        with patch('client.core.behavior_detector.YOLO'), \
             patch('os.path.exists', return_value=True):
            self.detector = BehaviorDetector("test_model.pt")
    
    def test_detect_no_model(self):
        """测试模型未加载时的检测"""
        self.detector.model = None
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        result = self.detector.detect(frame)
        
        assert result == []
    
    @patch('time.time')
    def test_detect_success_with_results(self, mock_time):
        """测试成功检测到目标（使用实际类别映射 CLASS_ID_TO_NAME）"""
        mock_time.side_effect = [0.0, 0.1, 0.2, 0.3]
        
        mock_boxes = Mock()
        mock_boxes.xyxy = [Mock()]
        mock_boxes.xyxy[0].cpu.return_value.numpy.return_value = np.array([100, 200, 300, 400])
        mock_boxes.conf = [Mock()]
        mock_boxes.conf[0].cpu.return_value.numpy.return_value = 0.85
        mock_boxes.cls = [Mock()]
        # class_id=2 → phone（根据 CLASS_ID_TO_NAME）
        mock_boxes.cls[0].cpu.return_value.numpy.return_value = 2
        mock_boxes.__len__ = Mock(return_value=1)
        
        mock_result = Mock()
        mock_result.boxes = mock_boxes
        mock_result.names = {2: "phone"}
        
        self.detector.model.return_value = [mock_result]
        
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        detections = self.detector.detect(frame)
        
        assert len(detections) == 1
        assert detections[0]["class"] == "phone"
        assert detections[0]["confidence"] == 0.85
        assert detections[0]["bbox"] == [100, 200, 300, 400]
    
    @patch('time.time')
    def test_detect_slow_inference_warning(self, mock_time):
        """测试推理耗时过长的警告"""
        mock_time.side_effect = [0.0, 0.25, 0.3, 0.4]
        
        mock_result = Mock()
        mock_result.boxes = None
        self.detector.model.return_value = [mock_result]
        
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        with patch.object(self.detector.logger, 'warning') as mock_warning:
            self.detector.detect(frame)
            mock_warning.assert_called_once()
            assert "推理耗时过长" in mock_warning.call_args[0][0]
    
    def test_detect_no_boxes(self):
        """测试检测结果中没有边界框"""
        mock_result = Mock()
        mock_result.boxes = None
        self.detector.model.return_value = [mock_result]
        
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        detections = self.detector.detect(frame)
        
        assert detections == []
    
    def test_detect_face_class_filtered(self):
        """测试 class_id=0 (face) 被过滤掉"""
        mock_boxes = Mock()
        mock_boxes.xyxy = [Mock()]
        mock_boxes.xyxy[0].cpu.return_value.numpy.return_value = np.array([100, 200, 300, 400])
        mock_boxes.conf = [Mock()]
        mock_boxes.conf[0].cpu.return_value.numpy.return_value = 0.85
        mock_boxes.cls = [Mock()]
        mock_boxes.cls[0].cpu.return_value.numpy.return_value = 0  # face，应被过滤
        mock_boxes.__len__ = Mock(return_value=1)
        
        mock_result = Mock()
        mock_result.boxes = mock_boxes
        mock_result.names = {0: "face"}
        
        self.detector.model.return_value = [mock_result]
        
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        detections = self.detector.detect(frame)
        
        assert detections == []
    
    def test_detect_multiple_objects(self):
        """测试检测到多个目标（phone + smoke）"""
        mock_boxes = Mock()
        mock_boxes.xyxy = [Mock(), Mock()]
        mock_boxes.xyxy[0].cpu.return_value.numpy.return_value = np.array([100, 200, 300, 400])
        mock_boxes.xyxy[1].cpu.return_value.numpy.return_value = np.array([500, 100, 600, 300])
        
        mock_boxes.conf = [Mock(), Mock()]
        mock_boxes.conf[0].cpu.return_value.numpy.return_value = 0.85
        mock_boxes.conf[1].cpu.return_value.numpy.return_value = 0.92
        
        mock_boxes.cls = [Mock(), Mock()]
        mock_boxes.cls[0].cpu.return_value.numpy.return_value = 2  # phone
        mock_boxes.cls[1].cpu.return_value.numpy.return_value = 1  # smoke
        mock_boxes.__len__ = Mock(return_value=2)
        
        mock_result = Mock()
        mock_result.boxes = mock_boxes
        mock_result.names = {2: "phone", 1: "smoke"}
        
        self.detector.model.return_value = [mock_result]
        
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        detections = self.detector.detect(frame)
        
        assert len(detections) == 2
        classes = {d["class"] for d in detections}
        assert classes == {"phone", "smoke"}
    
    def test_detect_exception_handling(self):
        """测试检测过程中的异常处理"""
        self.detector.model.side_effect = Exception("推理异常")
        
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        with patch.object(self.detector.logger, 'error') as mock_error:
            detections = self.detector.detect(frame)
            assert detections == []
            mock_error.assert_called_once()


class TestBehaviorDetectorCounters:
    """测试连续帧计数逻辑（使用实际类别名 smoke/phone/drink）"""
    
    def setup_method(self):
        """设置测试环境"""
        with patch('client.core.behavior_detector.YOLO'), \
             patch('os.path.exists', return_value=True):
            self.detector = BehaviorDetector("test_model.pt", consecutive_threshold=3)
    
    def test_update_counters_single_detection(self):
        """测试单个类别检测的计数更新"""
        detections = [{"class": "phone", "confidence": 0.8, "bbox": [100, 200, 300, 400]}]
        
        triggered = self.detector.update_counters(detections)
        
        assert self.detector.frame_counters["phone"] == 1
        assert self.detector.frame_counters["drink"] == 0
        assert self.detector.frame_counters["smoke"] == 0
        assert triggered == []
    
    def test_update_counters_trigger_threshold(self):
        """测试达到触发阈值"""
        detections = [{"class": "phone", "confidence": 0.8, "bbox": [100, 200, 300, 400]}]
        
        for i in range(2):
            triggered = self.detector.update_counters(detections)
            assert triggered == []
            assert self.detector.frame_counters["phone"] == i + 1
        
        with patch.object(self.detector.logger, 'info') as mock_info:
            triggered = self.detector.update_counters(detections)
            assert triggered == ["phone"]
            assert self.detector.frame_counters["phone"] == 0
            mock_info.assert_called_once()
    
    def test_update_counters_reset_on_missing(self):
        """测试未检测到时重置计数器"""
        detections_phone = [{"class": "phone", "confidence": 0.8, "bbox": [100, 200, 300, 400]}]
        detections_empty = []
        
        self.detector.update_counters(detections_phone)
        self.detector.update_counters(detections_phone)
        assert self.detector.frame_counters["phone"] == 2
        
        with patch.object(self.detector.logger, 'debug') as mock_debug:
            triggered = self.detector.update_counters(detections_empty)
            assert self.detector.frame_counters["phone"] == 0
            assert triggered == []
            mock_debug.assert_called_once()
    
    def test_update_counters_multiple_classes(self):
        """测试多个类别同时检测（使用实际类别 phone + drink）"""
        detections = [
            {"class": "phone", "confidence": 0.8, "bbox": [100, 200, 300, 400]},
            {"class": "drink", "confidence": 0.7, "bbox": [500, 100, 600, 300]}
        ]
        
        triggered = self.detector.update_counters(detections)
        
        assert self.detector.frame_counters["phone"] == 1
        assert self.detector.frame_counters["drink"] == 1
        assert self.detector.frame_counters["smoke"] == 0
        assert triggered == []
    
    def test_update_counters_multiple_triggers(self):
        """测试多个类别同时触发（phone + smoke）"""
        detections = [
            {"class": "phone", "confidence": 0.8, "bbox": [100, 200, 300, 400]},
            {"class": "smoke", "confidence": 0.9, "bbox": [500, 100, 600, 300]}
        ]
        
        for i in range(2):
            triggered = self.detector.update_counters(detections)
            assert triggered == []
        
        triggered = self.detector.update_counters(detections)
        assert set(triggered) == {"phone", "smoke"}
        assert self.detector.frame_counters["phone"] == 0
        assert self.detector.frame_counters["smoke"] == 0
    
    def test_update_counters_partial_reset(self):
        """测试部分类别重置（phone + drink）"""
        detections_both = [
            {"class": "phone", "confidence": 0.8, "bbox": [100, 200, 300, 400]},
            {"class": "drink", "confidence": 0.7, "bbox": [500, 100, 600, 300]}
        ]
        detections_phone_only = [
            {"class": "phone", "confidence": 0.8, "bbox": [100, 200, 300, 400]}
        ]
        
        self.detector.update_counters(detections_both)
        self.detector.update_counters(detections_both)
        assert self.detector.frame_counters["phone"] == 2
        assert self.detector.frame_counters["drink"] == 2
        
        triggered = self.detector.update_counters(detections_phone_only)
        assert self.detector.frame_counters["phone"] == 0
        assert self.detector.frame_counters["drink"] == 0
        assert triggered == ["phone"]


class TestBehaviorDetectorProcessFrame:
    """测试完整的帧处理流程"""
    
    def setup_method(self):
        """设置测试环境"""
        with patch('client.core.behavior_detector.YOLO'), \
             patch('os.path.exists', return_value=True):
            self.detector = BehaviorDetector("test_model.pt", consecutive_threshold=2)
    
    def test_process_frame_integration(self):
        """测试完整的帧处理流程"""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        mock_detections = [{"class": "phone", "confidence": 0.8, "bbox": [100, 200, 300, 400]}]
        
        with patch.object(self.detector, 'detect', return_value=mock_detections):
            detections, triggered = self.detector.process_frame(frame)
            assert detections == mock_detections
            assert triggered == []
            assert self.detector.frame_counters["phone"] == 1
            
            detections, triggered = self.detector.process_frame(frame)
            assert detections == mock_detections
            assert triggered == ["phone"]
            assert self.detector.frame_counters["phone"] == 0


class TestBehaviorDetectorUtilityMethods:
    """测试工具方法"""
    
    def setup_method(self):
        """设置测试环境"""
        with patch('client.core.behavior_detector.YOLO'), \
             patch('os.path.exists', return_value=True):
            self.detector = BehaviorDetector("test_model.pt")
    
    def test_reset(self):
        """测试重置计数器"""
        self.detector.frame_counters["phone"] = 5
        self.detector.frame_counters["drink"] = 3
        self.detector.frame_counters["smoke"] = 7
        
        with patch.object(self.detector.logger, 'info') as mock_info:
            self.detector.reset()
            mock_info.assert_called_once()
        
        assert self.detector.frame_counters["phone"] == 0
        assert self.detector.frame_counters["drink"] == 0
        assert self.detector.frame_counters["smoke"] == 0
    
    def test_get_severity(self):
        """测试获取危险等级（实际类别名）"""
        assert self.detector.get_severity("phone") == "medium"
        assert self.detector.get_severity("drink") == "low"
        assert self.detector.get_severity("smoke") == "high"
        assert self.detector.get_severity("unknown") == "medium"
    
    def test_get_frame_counter(self):
        """测试获取单个计数器"""
        self.detector.frame_counters["phone"] = 5
        
        assert self.detector.get_frame_counter("phone") == 5
        assert self.detector.get_frame_counter("drink") == 0
        assert self.detector.get_frame_counter("unknown") == 0
    
    def test_get_all_counters(self):
        """测试获取所有计数器（实际类别名）"""
        self.detector.frame_counters["phone"] = 3
        self.detector.frame_counters["smoke"] = 1
        
        counters = self.detector.get_all_counters()
        
        assert counters == {"smoke": 1, "phone": 3, "drink": 0}
        counters["phone"] = 999
        assert self.detector.frame_counters["phone"] == 3
    
    def test_is_model_loaded(self):
        """测试模型加载状态检查"""
        assert self.detector.is_model_loaded() is True
        
        self.detector.model = None
        assert self.detector.is_model_loaded() is False
    
    def test_supported_classes(self):
        """测试支持的类别列表（实际类别名）"""
        classes = self.detector.supported_classes
        assert set(classes) == {"phone", "smoke", "drink"}
    
    def test_class_severity_map(self):
        """测试类别-危险等级映射（实际类别名）"""
        severity_map = self.detector.class_severity_map
        expected = {"phone": "medium", "drink": "low", "smoke": "high"}
        assert severity_map == expected
        
        severity_map["phone"] = "high"
        assert self.detector.CLASS_SEVERITY_MAP["phone"] == "medium"


class TestBehaviorDetectorEdgeCases:
    """测试边界情况和异常场景"""
    
    def setup_method(self):
        """设置测试环境"""
        with patch('client.core.behavior_detector.YOLO'), \
             patch('os.path.exists', return_value=True):
            self.detector = BehaviorDetector("test_model.pt", consecutive_threshold=1)
    
    def test_threshold_one_immediate_trigger(self):
        """测试阈值为1时立即触发"""
        detections = [{"class": "phone", "confidence": 0.8, "bbox": [100, 200, 300, 400]}]
        
        triggered = self.detector.update_counters(detections)
        
        assert triggered == ["phone"]
        assert self.detector.frame_counters["phone"] == 0
    
    def test_empty_detections(self):
        """测试空检测结果"""
        self.detector.frame_counters["phone"] = 5
        
        triggered = self.detector.update_counters([])
        
        assert triggered == []
        assert self.detector.frame_counters["phone"] == 0
    
    def test_invalid_detection_format(self):
        """测试无效的检测结果格式"""
        invalid_detections = [{"confidence": 0.8, "bbox": [100, 200, 300, 400]}]
        
        with pytest.raises(KeyError):
            self.detector.update_counters(invalid_detections)
    
    def test_zero_threshold(self):
        """测试阈值为0的边界情况"""
        with patch('client.core.behavior_detector.YOLO'), \
             patch('os.path.exists', return_value=True):
            detector = BehaviorDetector("test_model.pt", consecutive_threshold=0)
            
            detections = [{"class": "phone", "confidence": 0.8, "bbox": [100, 200, 300, 400]}]
            triggered = detector.update_counters(detections)
            
            assert triggered == ["phone"]


class TestBehaviorDetectorIntegration:
    """集成测试"""
    
    @patch('client.core.behavior_detector.YOLO')
    @patch('os.path.exists')
    def test_full_workflow(self, mock_exists, mock_yolo):
        """测试完整工作流程"""
        mock_exists.return_value = True
        mock_model = Mock()
        mock_yolo.return_value = mock_model
        
        detector = BehaviorDetector("test_model.pt", consecutive_threshold=2)
        
        # class_id=2 → phone
        mock_boxes = Mock()
        mock_boxes.xyxy = [Mock()]
        mock_boxes.xyxy[0].cpu.return_value.numpy.return_value = np.array([100, 200, 300, 400])
        mock_boxes.conf = [Mock()]
        mock_boxes.conf[0].cpu.return_value.numpy.return_value = 0.85
        mock_boxes.cls = [Mock()]
        mock_boxes.cls[0].cpu.return_value.numpy.return_value = 2
        mock_boxes.__len__ = Mock(return_value=1)
        
        mock_result = Mock()
        mock_result.boxes = mock_boxes
        mock_result.names = {2: "phone"}
        
        mock_model.return_value = [mock_result]
        
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # 第一帧：检测到但不触发
        detections, triggered = detector.process_frame(frame)
        assert len(detections) == 1
        assert detections[0]["class"] == "phone"
        assert triggered == []
        assert detector.get_frame_counter("phone") == 1
        
        # 第二帧：应该触发
        detections, triggered = detector.process_frame(frame)
        assert len(detections) == 1
        assert triggered == ["phone"]
        assert detector.get_frame_counter("phone") == 0
        
        detector.reset()
        assert detector.get_all_counters() == {"smoke": 0, "phone": 0, "drink": 0}


if __name__ == "__main__":
    pytest.main([__file__])
