"""
YOLOv8 性能测试脚本

测试不同配置下的推理速度，帮助选择最优配置。

使用方法:
    python test_yolo_performance.py
    
注意: 这不是 pytest 测试，请直接用 python 运行。
"""

import sys
import os
import time
import numpy as np

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from client.core.behavior_detector import BehaviorDetector


def run_inference_speed_test(model_path: str, inference_size: int, use_half: bool, num_iterations: int = 50):
    """
    测试指定配置下的推理速度
    
    Args:
        model_path: 模型路径
        inference_size: 推理图像尺寸
        use_half: 是否使用半精度
        num_iterations: 测试迭代次数
    """
    print(f"\n{'='*60}")
    print(f"测试配置: 尺寸={inference_size}, 半精度={use_half}")
    print(f"{'='*60}")
    
    try:
        # 创建检测器
        detector = BehaviorDetector(
            model_path=model_path,
            consecutive_threshold=10,
            inference_size=inference_size,
            use_half=use_half
        )
        
        # 检查设备
        print(f"设备: {detector.device}")
        print(f"GPU 可用: {detector.is_gpu_available}")
        
        # 创建测试图像
        test_frame = np.random.randint(0, 255, (720, 1280, 3), dtype=np.uint8)
        
        # 预热（第一次推理通常较慢）
        print("预热中...")
        for _ in range(5):
            _ = detector.detect(test_frame)
        
        # 正式测试
        print(f"开始测试 {num_iterations} 次推理...")
        inference_times = []
        
        for i in range(num_iterations):
            start_time = time.time()
            detections = detector.detect(test_frame)
            inference_time = (time.time() - start_time) * 1000  # 转换为毫秒
            inference_times.append(inference_time)
            
            if (i + 1) % 10 == 0:
                print(f"  进度: {i+1}/{num_iterations}")
        
        # 统计结果
        avg_time = np.mean(inference_times)
        min_time = np.min(inference_times)
        max_time = np.max(inference_times)
        std_time = np.std(inference_times)
        
        print(f"\n结果统计:")
        print(f"  平均推理时间: {avg_time:.1f} ms")
        print(f"  最小推理时间: {min_time:.1f} ms")
        print(f"  最大推理时间: {max_time:.1f} ms")
        print(f"  标准差: {std_time:.1f} ms")
        print(f"  FPS: {1000/avg_time:.1f}")
        
        # 性能评估
        if avg_time < 50:
            print(f"  性能评级: ⭐⭐⭐⭐⭐ 优秀")
        elif avg_time < 100:
            print(f"  性能评级: ⭐⭐⭐⭐ 良好")
        elif avg_time < 200:
            print(f"  性能评级: ⭐⭐⭐ 可接受")
        elif avg_time < 400:
            print(f"  性能评级: ⭐⭐ 较慢")
        else:
            print(f"  性能评级: ⭐ 很慢")
        
        # 清理
        detector.close()
        
        return avg_time
        
    except Exception as e:
        print(f"测试失败: {e}")
        return None


def main():
    """主测试函数"""
    print("YOLOv8 性能测试工具")
    print("="*60)
    
    # 模型路径
    model_path = "yolov8n.pt"
    
    # 检查 GPU 可用性
    try:
        import torch
        gpu_available = torch.cuda.is_available()
        if gpu_available:
            print(f"✓ GPU 可用: {torch.cuda.get_device_name(0)}")
            print(f"  CUDA 版本: {torch.version.cuda}")
        else:
            print("✗ GPU 不可用，将使用 CPU")
    except ImportError:
        print("✗ PyTorch 未安装")
        gpu_available = False
    
    # 测试配置列表
    test_configs = [
        # (inference_size, use_half, description)
        (640, False, "高精度模式"),
        (416, False, "平衡模式"),
        (320, False, "快速模式"),
    ]
    
    # 如果 GPU 可用，添加半精度测试
    if gpu_available:
        test_configs.extend([
            (640, True, "高精度 + FP16"),
            (416, True, "平衡 + FP16"),
            (320, True, "快速 + FP16"),
        ])
    
    # 运行测试
    results = {}
    for size, half, desc in test_configs:
        avg_time = run_inference_speed_test(model_path, size, half, num_iterations=30)
        if avg_time is not None:
            results[desc] = avg_time
    
    # 汇总结果
    print(f"\n{'='*60}")
    print("测试汇总")
    print(f"{'='*60}")
    print(f"{'配置':<20} {'平均时间':<15} {'FPS':<10} {'评级'}")
    print(f"{'-'*60}")
    
    for desc, avg_time in results.items():
        fps = 1000 / avg_time
        if avg_time < 50:
            rating = "⭐⭐⭐⭐⭐"
        elif avg_time < 100:
            rating = "⭐⭐⭐⭐"
        elif avg_time < 200:
            rating = "⭐⭐⭐"
        elif avg_time < 400:
            rating = "⭐⭐"
        else:
            rating = "⭐"
        
        print(f"{desc:<20} {avg_time:>6.1f} ms      {fps:>5.1f}      {rating}")
    
    # 推荐配置
    print(f"\n{'='*60}")
    print("推荐配置")
    print(f"{'='*60}")
    
    if gpu_available:
        print("✓ 检测到 GPU，推荐配置:")
        print("  inference_size: 320")
        print("  use_half: true")
        print("  预期性能: 10-30 ms/帧")
    else:
        print("✗ 未检测到 GPU，推荐配置:")
        print("  inference_size: 320")
        print("  use_half: false")
        print("  预期性能: 150-250 ms/帧")
    
    print(f"\n在 config.yaml 中更新配置:")
    print("yolo:")
    print("  inference_timeout_ms: 200")
    if gpu_available:
        print("  inference_size: 320")
        print("  use_half: true")
    else:
        print("  inference_size: 320")
        print("  use_half: false")


if __name__ == "__main__":
    main()
