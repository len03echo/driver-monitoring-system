"""
测试 YOLOv8 检测功能启用

验证：
1. BehaviorDetector 已启用
2. 检测线程中有绘制 YOLOv8 结果的方法
3. 启动监测时启用了行为检测
"""
import sys
import os
import pytest
from unittest.mock import Mock, patch

# 添加路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'client'))


def test_behavior_detector_enabled_in_main_window():
    """测试主窗口中启用了行为检测器"""
    # 直接检查代码中是否启用了 BehaviorDetector
    main_window_path = os.path.join(os.path.dirname(__file__), '..', 'client', 'ui', 'main_window.py')
    
    with open(main_window_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 查找 create_detectors 方法
    # 应该包含 behavior_detector = BehaviorDetector(
    assert 'behavior_detector = BehaviorDetector(' in content, \
        "create_detectors 方法中应该创建 BehaviorDetector 实例"
    
    # 确保不是注释掉的
    lines = content.split('\n')
    found_creation = False
    for line in lines:
        if 'behavior_detector = BehaviorDetector(' in line:
            # 检查这一行不是注释
            stripped = line.strip()
            if not stripped.startswith('#'):
                found_creation = True
                break
    
    assert found_creation, "BehaviorDetector 的创建不应该被注释掉"
    
    print("✓ BehaviorDetector 已在主窗口中启用")


def test_detection_thread_has_draw_method():
    """测试检测线程有绘制 YOLOv8 结果的方法"""
    from core.detection_thread import DetectionThread
    
    thread = DetectionThread()
    
    # 验证方法存在
    assert hasattr(thread, '_draw_yolo_detections'), \
        "DetectionThread 应该有 _draw_yolo_detections 方法"
    
    # 验证方法可调用
    assert callable(thread._draw_yolo_detections), \
        "_draw_yolo_detections 应该是可调用的方法"
    
    print("✓ DetectionThread 有 _draw_yolo_detections 方法")


def test_draw_yolo_detections_functionality():
    """测试绘制 YOLOv8 检测结果的功能"""
    import numpy as np
    from core.detection_thread import DetectionThread
    
    thread = DetectionThread()
    
    # 创建测试帧
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # 创建测试检测结果
    detections = [
        {
            "class": "phone",
            "confidence": 0.85,
            "bbox": [100, 100, 200, 200]
        },
        {
            "class": "cup",
            "confidence": 0.75,
            "bbox": [300, 150, 400, 250]
        }
    ]
    
    # 调用绘制方法
    annotated_frame = thread._draw_yolo_detections(frame, detections)
    
    # 验证返回的是 numpy 数组
    assert isinstance(annotated_frame, np.ndarray)
    
    # 验证形状相同
    assert annotated_frame.shape == frame.shape
    
    # 验证帧被修改了（不是全黑）
    assert np.any(annotated_frame != frame), "绘制后的帧应该与原始帧不同"
    
    print("✓ _draw_yolo_detections 方法功能正常")


def test_behavior_detection_enabled_on_start():
    """测试启动监测时启用了行为检测"""
    # 这个测试需要检查代码中的配置
    # 读取 main_window.py 文件内容
    main_window_path = os.path.join(os.path.dirname(__file__), '..', 'client', 'ui', 'main_window.py')
    
    with open(main_window_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 查找 start_monitoring 方法中的配置
    # 应该包含 enable_behavior=True
    assert 'enable_behavior=True' in content, \
        "启动监测时应该设置 enable_behavior=True"
    
    print("✓ 启动监测时启用了行为检测")


if __name__ == "__main__":
    print("=" * 60)
    print("测试 YOLOv8 检测功能启用")
    print("=" * 60)
    
    test_behavior_detector_enabled_in_main_window()
    print()
    
    test_detection_thread_has_draw_method()
    print()
    
    test_draw_yolo_detections_functionality()
    print()
    
    test_behavior_detection_enabled_on_start()
    
    print("\n" + "=" * 60)
    print("所有测试通过！✓")
    print("=" * 60)
