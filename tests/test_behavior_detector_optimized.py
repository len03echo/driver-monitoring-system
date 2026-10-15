"""
测试 BehaviorDetector 的性能优化功能

验证新增的 inference_size 和 use_half 参数是否正常工作。
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
import numpy as np

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from client.core.behavior_detector import BehaviorDetector


class TestBehaviorDetectorOptimization:
    """测试 BehaviorDetector 的性能优化参数"""
    
    @patch('client.core.behavior_detector.YOLO')
    def test_init_with_inference_size(self, mock_yolo):
        """测试使用自定义推理尺寸初始化"""
        mock_model = Mock()
        mock_yolo.return_value = mock_model
        
        detector = BehaviorDetector(
            "test_model.pt",
            consecutive_threshold=10,
            inference_size=320
        )
        
        assert detector.inference_size == 320
        assert detector.model_path == "test_model.pt"
        print("✓ 自定义推理尺寸参数正常工作")
    
    @patch('client.core.behavior_detector.YOLO')
    def test_init_with_use_half(self, mock_yolo):
        """测试使用半精度参数初始化"""
        mock_model = Mock()
        mock_yolo.return_value = mock_model
        
        detector = BehaviorDetector(
            "test_model.pt",
            consecutive_threshold=10,
            inference_size=320,
            use_half=True
        )
        
        assert detector.use_half == True
        assert detector.inference_size == 320
        print("✓ 半精度参数正常工作")
    
    @patch('client.core.behavior_detector.YOLO')
    def test_default_parameters(self, mock_yolo):
        """测试默认参数值"""
        mock_model = Mock()
        mock_yolo.return_value = mock_model
        
        detector = BehaviorDetector("test_model.pt")
        
        assert detector.inference_size == 320  # 默认值
        assert detector.use_half == False      # 默认值
        assert detector.consecutive_threshold == 10
        print("✓ 默认参数值正确")
    
    @patch('client.core.behavior_detector.YOLO')
    def test_gpu_detection(self, mock_yolo):
        """测试 GPU 检测逻辑"""
        mock_model = Mock()
        mock_model.to = Mock()
        mock_model.model = Mock()
        mock_yolo.return_value = mock_model
        
        # 模拟 torch 在 _load_model 内部导入
        import torch
        original_cuda_available = torch.cuda.is_available
        
        try:
            # 临时修改 torch.cuda.is_available 返回 True
            torch.cuda.is_available = lambda: True
            torch.cuda.get_device_name = lambda x: "NVIDIA GeForce RTX 3080"
            
            detector = BehaviorDetector(
                "test_model.pt",
                inference_size=320,
                use_half=True
            )
            
            # 验证 GPU 被检测到
            assert detector.is_gpu_available == True
            assert detector.device == 'cuda'
            print("✓ GPU 检测逻辑正常")
        finally:
            # 恢复原始函数
            torch.cuda.is_available = original_cuda_available
    
    @patch('client.core.behavior_detector.YOLO')
    def test_cpu_fallback(self, mock_yolo):
        """测试 CPU 回退逻辑"""
        mock_model = Mock()
        mock_yolo.return_value = mock_model
        
        # 模拟 torch 在 _load_model 内部导入
        import torch
        original_cuda_available = torch.cuda.is_available
        
        try:
            # 临时修改 torch.cuda.is_available 返回 False
            torch.cuda.is_available = lambda: False
            
            detector = BehaviorDetector(
                "test_model.pt",
                inference_size=320,
                use_half=True
            )
            
            # 验证回退到 CPU
            assert detector.device == 'cpu'
            # use_half 应该被自动禁用
            assert detector.use_half == False
            print("✓ CPU 回退逻辑正常")
        finally:
            # 恢复原始函数
            torch.cuda.is_available = original_cuda_available
    
    @patch('client.core.behavior_detector.YOLO')
    def test_detect_with_optimized_parameters(self, mock_yolo):
        """测试优化参数是否正确传递给推理函数"""
        mock_model = Mock()
        mock_result = Mock()
        mock_result.boxes = None
        mock_model.return_value = [mock_result]
        mock_yolo.return_value = mock_model
        
        detector = BehaviorDetector(
            "test_model.pt",
            inference_size=416,
            use_half=False
        )
        
        # 创建测试帧
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # 执行检测
        detections = detector.detect(test_frame)
        
        # 验证模型被调用，并且传入了正确的参数
        assert mock_model.called
        call_args = mock_model.call_args
        
        # 检查 imgsz 参数
        assert 'imgsz' in call_args.kwargs
        assert call_args.kwargs['imgsz'] == 416
        
        # 检查 device 参数
        assert 'device' in call_args.kwargs
        
        print("✓ 优化参数正确传递给推理函数")
    
    @patch('client.core.behavior_detector.YOLO')
    def test_different_inference_sizes(self, mock_yolo):
        """测试不同的推理尺寸"""
        mock_model = Mock()
        mock_yolo.return_value = mock_model
        
        sizes = [320, 416, 640]
        
        for size in sizes:
            detector = BehaviorDetector(
                "test_model.pt",
                inference_size=size
            )
            assert detector.inference_size == size
        
        print(f"✓ 支持多种推理尺寸: {sizes}")
    
    @patch('client.core.behavior_detector.YOLO')
    def test_performance_warning_includes_config_info(self, mock_yolo):
        """测试性能警告包含配置信息"""
        mock_model = Mock()
        mock_result = Mock()
        mock_result.boxes = None
        
        # 模拟慢速推理
        def slow_inference(*args, **kwargs):
            import time
            time.sleep(0.25)  # 250ms
            return [mock_result]
        
        mock_model.side_effect = slow_inference
        mock_yolo.return_value = mock_model
        
        detector = BehaviorDetector(
            "test_model.pt",
            inference_size=640,
            use_half=False
        )
        
        # 创建测试帧
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # 执行检测（应该触发警告）
        with patch.object(detector.logger, 'warning') as mock_warning:
            detections = detector.detect(test_frame)
            
            # 验证警告被调用
            assert mock_warning.called
            warning_message = mock_warning.call_args[0][0]
            
            # 验证警告消息包含配置信息
            assert 'ms' in warning_message
            assert '设备' in warning_message or 'device' in warning_message.lower()
            
            print("✓ 性能警告包含详细配置信息")


def test_main_window_uses_optimized_parameters():
    """测试主窗口是否使用了优化参数"""
    import sys
    import os
    
    # 读取 main_window.py 文件
    main_window_path = os.path.join(
        os.path.dirname(__file__), 
        '..', 
        'client', 
        'ui', 
        'main_window.py'
    )
    
    with open(main_window_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 验证 create_detectors 方法使用了新参数
    assert 'inference_size=' in content, \
        "main_window.py 应该使用 inference_size 参数"
    
    assert 'use_half=' in content, \
        "main_window.py 应该使用 use_half 参数"
    
    assert 'self.config.yolo.inference_size' in content, \
        "应该从配置文件读取 inference_size"
    
    assert 'self.config.yolo.use_half' in content, \
        "应该从配置文件读取 use_half"
    
    print("✓ 主窗口正确使用了优化参数")


def test_config_file_has_optimization_settings():
    """测试配置文件包含优化设置"""
    import yaml
    
    config_path = os.path.join(
        os.path.dirname(__file__), 
        '..', 
        'client', 
        'config.yaml'
    )
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 验证 yolo 配置存在
    assert 'yolo' in config, "配置文件应该包含 yolo 部分"
    
    yolo_config = config['yolo']
    
    # 验证优化参数存在
    assert 'inference_size' in yolo_config, \
        "yolo 配置应该包含 inference_size"
    
    assert 'use_half' in yolo_config, \
        "yolo 配置应该包含 use_half"
    
    # 验证参数值合理
    assert yolo_config['inference_size'] in [320, 416, 640], \
        "inference_size 应该是 320, 416 或 640"
    
    assert isinstance(yolo_config['use_half'], bool), \
        "use_half 应该是布尔值"
    
    print(f"✓ 配置文件包含优化设置:")
    print(f"  - inference_size: {yolo_config['inference_size']}")
    print(f"  - use_half: {yolo_config['use_half']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
