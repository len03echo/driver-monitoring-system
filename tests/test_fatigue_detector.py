"""
FatigueDetector 模块单元测试

测试基于 MediaPipe Face Mesh 的疲劳检测器功能：
- MediaPipe 初始化
- EAR/MAR 计算算法
- 头部角度计算
- 连续帧计数逻辑
- 疲劳触发机制
- 错误处理

依赖：
- pytest
- numpy
- unittest.mock
"""

import pytest
import numpy as np
import math
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Tuple

# 导入被测试的模块
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from client.core.fatigue_detector import FatigueDetector


class TestFatigueDetectorInit:
    """测试 FatigueDetector 初始化"""
    
    @patch('client.core.fatigue_detector.mp')
    def test_init_success(self, mock_mp):
        """测试成功初始化"""
        mock_face_mesh_class = Mock()
        mock_face_mesh_instance = Mock()
        mock_face_mesh_class.FaceMesh.return_value = mock_face_mesh_instance
        mock_mp.solutions.face_mesh = mock_face_mesh_class
        
        detector = FatigueDetector()
        
        assert detector.face_mesh == mock_face_mesh_instance
        assert detector.frame_counters == {"eye_closed": 0, "yawning": 0, "head_down": 0}
        mock_face_mesh_class.FaceMesh.assert_called_once()
    
    @patch('client.core.fatigue_detector.mp')
    def test_init_mediapipe_config(self, mock_mp):
        """测试 MediaPipe 配置参数"""
        mock_face_mesh_class = Mock()
        mock_mp.solutions.face_mesh = mock_face_mesh_class
        
        detector = FatigueDetector()
        
        # 验证 FaceMesh 调用参数
        call_args = mock_face_mesh_class.FaceMesh.call_args
        assert call_args[1]['static_image_mode'] == False
        assert call_args[1]['max_num_faces'] == 1
        assert call_args[1]['refine_landmarks'] == True
        assert call_args[1]['min_detection_confidence'] == 0.5
        assert call_args[1]['min_tracking_confidence'] == 0.5


class TestFatigueDetectorEARCalculation:
    """测试 EAR 计算算法"""
    
    def setup_method(self):
        """设置测试环境"""
        with patch('client.core.fatigue_detector.mp') as mock_mp:
            mock_mp.solutions.face_mesh = Mock()
            self.detector = FatigueDetector()
    
    def test_calculate_ear_normal_eye(self):
        """测试正常睁眼状态的 EAR 计算"""
        # 模拟睁眼状态的6个关键点 (水平椭圆形)
        eye_points = [
            (100, 150),  # 左眼角
            (110, 145),  # 上眼睑1
            (120, 145),  # 上眼睑2
            (140, 150),  # 右眼角
            (120, 155),  # 下眼睑2
            (110, 155)   # 下眼睑1
        ]
        
        ear = self.detector._calculate_ear(eye_points)
        
        # 睁眼状态 EAR 应该大于等于阈值 0.25
        assert ear >= 0.25
        assert 0.2 < ear < 0.5  # 合理范围
    
    def test_calculate_ear_closed_eye(self):
        """测试闭眼状态的 EAR 计算"""
        # 模拟闭眼状态的6个关键点 (水平线形)
        eye_points = [
            (100, 150),  # 左眼角
            (110, 150),  # 上眼睑1 (与下眼睑重合)
            (120, 150),  # 上眼睑2 (与下眼睑重合)
            (140, 150),  # 右眼角
            (120, 150),  # 下眼睑2
            (110, 150)   # 下眼睑1
        ]
        
        ear = self.detector._calculate_ear(eye_points)
        
        # 闭眼状态 EAR 应该接近 0
        assert ear < 0.1
    
    def test_calculate_ear_invalid_points(self):
        """测试无效关键点数量"""
        # 关键点数量不足
        eye_points = [(100, 150), (110, 145)]
        
        ear = self.detector._calculate_ear(eye_points)
        
        # 应该返回默认值 1.0
        assert ear == 1.0
    
    def test_calculate_ear_zero_horizontal(self):
        """测试水平距离为0的边界情况"""
        # 所有点在同一垂直线上
        eye_points = [
            (100, 140),  # 左眼角
            (100, 145),  # 上眼睑1
            (100, 145),  # 上眼睑2
            (100, 140),  # 右眼角 (与左眼角相同位置，水平距离为0)
            (100, 155),  # 下眼睑2
            (100, 155)   # 下眼睑1
        ]
        
        ear = self.detector._calculate_ear(eye_points)
        
        # 水平距离为0时应该返回默认值 1.0
        assert ear == 1.0


class TestFatigueDetectorMARCalculation:
    """测试 MAR 计算算法"""
    
    def setup_method(self):
        """设置测试环境"""
        with patch('client.core.fatigue_detector.mp') as mock_mp:
            mock_mp.solutions.face_mesh = Mock()
            self.detector = FatigueDetector()
    
    def test_calculate_mar_closed_mouth(self):
        """测试闭嘴状态的 MAR 计算"""
        # 模拟闭嘴状态的8个关键点 (水平线形)
        mouth_points = [
            (100, 200),  # 左嘴角
            (110, 200),  # 上唇1
            (120, 200),  # 上唇2
            (130, 200),  # 上唇3
            (140, 200),  # 右嘴角
            (130, 200),  # 下唇3
            (120, 200),  # 下唇2
            (110, 200)   # 下唇1
        ]
        
        mar = self.detector._calculate_mar(mouth_points)
        
        # 闭嘴状态 MAR 应该接近 0
        assert mar < 0.1
    
    def test_calculate_mar_open_mouth(self):
        """测试张嘴状态的 MAR 计算"""
        # 模拟张嘴状态的8个关键点 (椭圆形) - 增大垂直距离
        mouth_points = [
            (100, 200),  # 左嘴角
            (110, 185),  # 上唇1 (更高)
            (120, 180),  # 上唇2 (更高)
            (130, 185),  # 上唇3 (更高)
            (140, 200),  # 右嘴角
            (130, 215),  # 下唇3 (更低)
            (120, 220),  # 下唇2 (更低)
            (110, 215)   # 下唇1 (更低)
        ]
        
        mar = self.detector._calculate_mar(mouth_points)
        
        # 张嘴状态 MAR 应该大于阈值 0.6
        assert mar > 0.6
    
    def test_calculate_mar_invalid_points(self):
        """测试无效关键点数量"""
        # 关键点数量不足
        mouth_points = [(100, 200), (110, 190)]
        
        mar = self.detector._calculate_mar(mouth_points)
        
        # 应该返回默认值 0.0
        assert mar == 0.0
    
    def test_calculate_mar_zero_horizontal(self):
        """测试水平距离为0的边界情况"""
        # 所有点在同一垂直线上
        mouth_points = [
            (100, 190),  # 左嘴角
            (100, 195),  # 上唇1
            (100, 195),  # 上唇2
            (100, 195),  # 上唇3
            (100, 190),  # 右嘴角 (与左嘴角相同位置，水平距离为0)
            (100, 205),  # 下唇3
            (100, 205),  # 下唇2
            (100, 205)   # 下唇1
        ]
        
        mar = self.detector._calculate_mar(mouth_points)
        
        # 水平距离为0时应该返回默认值 0.0
        assert mar == 0.0


class TestFatigueDetectorHeadAngle:
    """测试头部角度计算"""
    
    def setup_method(self):
        """设置测试环境"""
        with patch('client.core.fatigue_detector.mp') as mock_mp:
            mock_mp.solutions.face_mesh = Mock()
            self.detector = FatigueDetector()
    
    def test_calculate_head_angle_normal(self):
        """测试正常头部姿态"""
        nose_tip = (320, 200)  # 鼻尖
        chin = (320, 300)      # 下巴 (正下方)
        
        angle = self.detector._calculate_head_angle(nose_tip, chin)
        
        # 正常姿态角度应该接近 0
        assert angle < 5  # 允许小误差
    
    def test_calculate_head_angle_left_tilt(self):
        """测试向左倾斜"""
        nose_tip = (320, 200)  # 鼻尖
        chin = (280, 300)      # 下巴向左偏移
        
        angle = self.detector._calculate_head_angle(nose_tip, chin)
        
        # 应该有一定角度
        assert 10 < angle < 45
    
    def test_calculate_head_angle_right_tilt(self):
        """测试向右倾斜"""
        nose_tip = (320, 200)  # 鼻尖
        chin = (360, 300)      # 下巴向右偏移
        
        angle = self.detector._calculate_head_angle(nose_tip, chin)
        
        # 应该有一定角度
        assert 10 < angle < 45
    
    def test_calculate_head_angle_extreme_tilt(self):
        """测试极端倾斜（低头）"""
        nose_tip = (320, 200)  # 鼻尖
        chin = (400, 250)      # 下巴大幅偏移
        
        angle = self.detector._calculate_head_angle(nose_tip, chin)
        
        # 极端倾斜应该超过阈值
        assert angle > 30


class TestFatigueDetectorDetection:
    """测试疲劳检测功能"""
    
    def setup_method(self):
        """设置测试环境"""
        with patch('client.core.fatigue_detector.mp') as mock_mp:
            mock_mp.solutions.face_mesh = Mock()
            self.detector = FatigueDetector()
    
    @patch('cv2.cvtColor')
    def test_detect_no_face(self, mock_cvtcolor):
        """测试未检测到人脸"""
        mock_cvtcolor.return_value = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # 模拟未检测到人脸
        self.detector.face_mesh.process.return_value.multi_face_landmarks = None
        
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        result = self.detector.detect(frame)
        
        assert result["face_detected"] == False
        assert result["ear"] == 1.0  # 默认值
        assert result["mar"] == 0.0  # 默认值
        assert result["head_angle"] == 0.0  # 默认值
    
    @patch('cv2.cvtColor')
    def test_detect_with_face(self, mock_cvtcolor):
        """测试检测到人脸"""
        mock_cvtcolor.return_value = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # 创建模拟的人脸关键点
        mock_landmarks = []
        # 创建478个关键点 (MediaPipe Face Mesh 标准)
        for i in range(478):
            mock_landmark = Mock()
            mock_landmark.x = 0.5  # 归一化坐标
            mock_landmark.y = 0.5
            mock_landmarks.append(mock_landmark)
        
        # 设置特定关键点用于计算
        # 左眼关键点
        for i, idx in enumerate(self.detector.LEFT_EYE_POINTS):
            mock_landmarks[idx].x = 0.3 + i * 0.02
            mock_landmarks[idx].y = 0.4
        
        # 右眼关键点
        for i, idx in enumerate(self.detector.RIGHT_EYE_POINTS):
            mock_landmarks[idx].x = 0.6 + i * 0.02
            mock_landmarks[idx].y = 0.4
        
        # 嘴巴关键点
        for i, idx in enumerate(self.detector.MOUTH_POINTS):
            mock_landmarks[idx].x = 0.45 + i * 0.01
            mock_landmarks[idx].y = 0.6
        
        # 鼻尖和下巴
        mock_landmarks[self.detector.NOSE_TIP].x = 0.5
        mock_landmarks[self.detector.NOSE_TIP].y = 0.5
        mock_landmarks[self.detector.CHIN].x = 0.5
        mock_landmarks[self.detector.CHIN].y = 0.7
        
        mock_face = Mock()
        mock_face.landmark = mock_landmarks
        
        self.detector.face_mesh.process.return_value.multi_face_landmarks = [mock_face]
        
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        result = self.detector.detect(frame)
        
        assert result["face_detected"] == True
        assert isinstance(result["ear"], float)
        assert isinstance(result["mar"], float)
        assert isinstance(result["head_angle"], float)


class TestFatigueDetectorCounters:
    """测试连续帧计数逻辑"""
    
    def setup_method(self):
        """设置测试环境"""
        with patch('client.core.fatigue_detector.mp') as mock_mp:
            mock_mp.solutions.face_mesh = Mock()
            self.detector = FatigueDetector()
    
    def test_update_counters_no_face(self):
        """测试未检测到人脸时重置计数器"""
        # 设置一些计数值
        self.detector.frame_counters["eye_closed"] = 5
        self.detector.frame_counters["yawning"] = 3
        
        detection_result = {"face_detected": False}
        
        with patch.object(self.detector.logger, 'debug') as mock_debug:
            triggered = self.detector.update_counters(detection_result)
            
            assert triggered == []
            assert self.detector.frame_counters["eye_closed"] == 0
            assert self.detector.frame_counters["yawning"] == 0
            assert self.detector.frame_counters["head_down"] == 0
    
    def test_update_counters_eye_closed_trigger(self):
        """测试闭眼触发"""
        detection_result = {
            "face_detected": True,
            "ear": 0.2,  # 低于阈值 0.25
            "mar": 0.3,  # 正常
            "head_angle": 10  # 正常
        }
        
        # 连续19帧不触发
        for i in range(19):
            triggered = self.detector.update_counters(detection_result)
            assert triggered == []
            assert self.detector.frame_counters["eye_closed"] == i + 1
        
        # 第20帧应该触发
        with patch.object(self.detector.logger, 'info') as mock_info:
            triggered = self.detector.update_counters(detection_result)
            assert triggered == ["eye_closed"]
            assert self.detector.frame_counters["eye_closed"] == 0  # 重置
            mock_info.assert_called_once()
    
    def test_update_counters_yawning_trigger(self):
        """测试哈欠触发（MAR 需超过默认阈值 0.8）"""
        detection_result = {
            "face_detected": True,
            "ear": 0.3,   # 正常
            "mar": 0.9,   # 高于默认阈值 0.8
            "head_angle": 10  # 正常
        }
        
        # 连续14帧不触发
        for i in range(14):
            triggered = self.detector.update_counters(detection_result)
            assert triggered == []
            assert self.detector.frame_counters["yawning"] == i + 1
        
        # 第15帧应该触发
        with patch.object(self.detector.logger, 'info') as mock_info:
            triggered = self.detector.update_counters(detection_result)
            assert triggered == ["yawning"]
            assert self.detector.frame_counters["yawning"] == 0  # 重置
            mock_info.assert_called_once()
    
    def test_update_counters_head_down_trigger(self):
        """测试低头触发"""
        detection_result = {
            "face_detected": True,
            "ear": 0.3,   # 正常
            "mar": 0.3,   # 正常
            "head_angle": 35  # 高于阈值 30
        }
        
        # 连续9帧不触发
        for i in range(9):
            triggered = self.detector.update_counters(detection_result)
            assert triggered == []
            assert self.detector.frame_counters["head_down"] == i + 1
        
        # 第10帧应该触发
        with patch.object(self.detector.logger, 'info') as mock_info:
            triggered = self.detector.update_counters(detection_result)
            assert triggered == ["head_down"]
            assert self.detector.frame_counters["head_down"] == 0  # 重置
            mock_info.assert_called_once()
    
    def test_update_counters_multiple_triggers(self):
        """测试多种疲劳同时触发"""
        detection_result = {
            "face_detected": True,
            "ear": 0.2,   # 闭眼
            "mar": 0.9,   # 哈欠（超过默认阈值 0.8）
            "head_angle": 35  # 低头
        }
        
        # 设置计数器接近触发阈值
        self.detector.frame_counters["eye_closed"] = 19
        self.detector.frame_counters["yawning"] = 14
        self.detector.frame_counters["head_down"] = 9
        
        triggered = self.detector.update_counters(detection_result)
        
        # 应该同时触发三种疲劳类型
        assert set(triggered) == {"eye_closed", "yawning", "head_down"}
        assert self.detector.frame_counters["eye_closed"] == 0
        assert self.detector.frame_counters["yawning"] == 0
        assert self.detector.frame_counters["head_down"] == 0
    
    def test_update_counters_reset_on_normal(self):
        """测试正常状态时重置计数器"""
        # 设置一些计数值
        self.detector.frame_counters["eye_closed"] = 10
        self.detector.frame_counters["yawning"] = 5
        self.detector.frame_counters["head_down"] = 3
        
        detection_result = {
            "face_detected": True,
            "ear": 0.3,   # 正常
            "mar": 0.3,   # 正常
            "head_angle": 10  # 正常
        }
        
        with patch.object(self.detector.logger, 'debug') as mock_debug:
            triggered = self.detector.update_counters(detection_result)
            
            assert triggered == []
            assert self.detector.frame_counters["eye_closed"] == 0
            assert self.detector.frame_counters["yawning"] == 0
            assert self.detector.frame_counters["head_down"] == 0
            # 应该记录3次debug日志（每个重置的计数器一次）
            assert mock_debug.call_count == 3


class TestFatigueDetectorUtilityMethods:
    """测试工具方法"""
    
    def setup_method(self):
        """设置测试环境"""
        with patch('client.core.fatigue_detector.mp') as mock_mp:
            mock_mp.solutions.face_mesh = Mock()
            self.detector = FatigueDetector()
    
    def test_process_frame_integration(self):
        """测试完整的帧处理流程"""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        mock_detection_result = {
            "face_detected": True,
            "ear": 0.2,
            "mar": 0.3,
            "head_angle": 10
        }
        
        with patch.object(self.detector, 'detect', return_value=mock_detection_result):
            detection_result, triggered = self.detector.process_frame(frame)
            
            assert detection_result == mock_detection_result
            assert isinstance(triggered, list)
    
    def test_reset(self):
        """测试重置计数器"""
        # 设置一些计数值
        self.detector.frame_counters["eye_closed"] = 15
        self.detector.frame_counters["yawning"] = 8
        self.detector.frame_counters["head_down"] = 5
        
        with patch.object(self.detector.logger, 'info') as mock_info:
            self.detector.reset()
            mock_info.assert_called_once()
        
        assert self.detector.frame_counters["eye_closed"] == 0
        assert self.detector.frame_counters["yawning"] == 0
        assert self.detector.frame_counters["head_down"] == 0
    
    def test_get_severity(self):
        """测试获取危险等级"""
        assert self.detector.get_severity("eye_closed") == "high"
        assert self.detector.get_severity("yawning") == "medium"
        assert self.detector.get_severity("head_down") == "medium"
        assert self.detector.get_severity("unknown") == "medium"  # 默认值
    
    def test_get_frame_counter(self):
        """测试获取单个计数器"""
        self.detector.frame_counters["eye_closed"] = 12
        
        assert self.detector.get_frame_counter("eye_closed") == 12
        assert self.detector.get_frame_counter("yawning") == 0
        assert self.detector.get_frame_counter("unknown") == 0
    
    def test_get_all_counters(self):
        """测试获取所有计数器"""
        self.detector.frame_counters["eye_closed"] = 8
        self.detector.frame_counters["head_down"] = 3
        
        counters = self.detector.get_all_counters()
        
        assert counters == {"eye_closed": 8, "yawning": 0, "head_down": 3}
        # 确保返回的是副本
        counters["eye_closed"] = 999
        assert self.detector.frame_counters["eye_closed"] == 8
    
    def test_supported_fatigue_types(self):
        """测试支持的疲劳类型列表"""
        types = self.detector.supported_fatigue_types
        assert set(types) == {"eye_closed", "yawning", "head_down"}
    
    def test_close(self):
        """测试资源释放"""
        with patch.object(self.detector.logger, 'info') as mock_info:
            self.detector.close()
            mock_info.assert_called_once()
        
        self.detector.face_mesh.close.assert_called_once()
    
    def test_context_manager(self):
        """测试上下文管理器"""
        with patch.object(self.detector, 'close') as mock_close:
            with self.detector as detector:
                assert detector == self.detector
            mock_close.assert_called_once()


class TestFatigueDetectorConstants:
    """测试常量和阈值"""
    
    def setup_method(self):
        """设置测试环境"""
        with patch('client.core.fatigue_detector.mp') as mock_mp:
            mock_mp.solutions.face_mesh = Mock()
            self.detector = FatigueDetector()
    
    def test_eye_points_constants(self):
        """测试眼部关键点常量"""
        assert len(self.detector.LEFT_EYE_POINTS) == 6
        assert len(self.detector.RIGHT_EYE_POINTS) == 6
        assert isinstance(self.detector.LEFT_EYE_POINTS[0], int)
        assert isinstance(self.detector.RIGHT_EYE_POINTS[0], int)
    
    def test_mouth_points_constants(self):
        """测试嘴部关键点常量"""
        assert len(self.detector.MOUTH_POINTS) == 8
        assert isinstance(self.detector.MOUTH_POINTS[0], int)
    
    def test_threshold_constants(self):
        """测试阈值常量"""
        assert self.detector.EAR_THRESHOLD == 0.25
        assert self.detector.MAR_THRESHOLD == 0.8   # 实际默认值为 0.8
        assert self.detector.HEAD_DOWN_THRESHOLD == 30
        
        assert self.detector.EYE_CLOSED_FRAMES == 20
        assert self.detector.YAWNING_FRAMES == 15
        assert self.detector.HEAD_DOWN_FRAMES == 10


if __name__ == "__main__":
    pytest.main([__file__])