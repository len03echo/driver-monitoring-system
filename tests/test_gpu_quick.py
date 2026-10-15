"""
快速测试 GPU 是否正确启用
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 配置日志
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from client.core.behavior_detector import BehaviorDetector
import numpy as np

print("="*60)
print("GPU 快速测试")
print("="*60)

# 检查 PyTorch CUDA
import torch
print(f"\n1. PyTorch CUDA 检查:")
print(f"   CUDA 可用: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"   CUDA 版本: {torch.version.cuda}")
    print(f"   GPU 设备: {torch.cuda.get_device_name(0)}")

# 创建检测器
print(f"\n2. 创建 BehaviorDetector:")
print("   (查看下方日志输出...)")
print()

detector = BehaviorDetector(
    model_path="yolov8n.pt",
    consecutive_threshold=10,
    inference_size=320,
    use_half=True
)

print()

print(f"\n3. 检测器配置:")
print(f"   设备: {detector.device}")
print(f"   GPU 可用: {detector.is_gpu_available}")
print(f"   推理尺寸: {detector.inference_size}")
print(f"   半精度: {detector.use_half}")

# 测试推理
print(f"\n4. 测试推理:")
test_frame = np.random.randint(0, 255, (720, 1280, 3), dtype=np.uint8)

import time

# 预热几次（第一次通常较慢）
print("   预热推理...")
for _ in range(3):
    _ = detector.detect(test_frame)

# 正式测试多次
print("   正式测试 10 次...")
times = []
for i in range(10):
    start = time.time()
    detections = detector.detect(test_frame)
    elapsed = (time.time() - start) * 1000
    times.append(elapsed)

avg_time = sum(times) / len(times)
min_time = min(times)
max_time = max(times)

print(f"   平均推理时间: {avg_time:.1f} ms")
print(f"   最小推理时间: {min_time:.1f} ms")
print(f"   最大推理时间: {max_time:.1f} ms")
print(f"   检测结果: {len(detections)} 个对象")

elapsed = avg_time  # 使用平均时间评估

if elapsed < 50:
    print(f"   性能: ⭐⭐⭐⭐⭐ 优秀 (GPU 正常工作)")
elif elapsed < 100:
    print(f"   性能: ⭐⭐⭐⭐ 良好")
elif elapsed < 200:
    print(f"   性能: ⭐⭐⭐ 可接受")
else:
    print(f"   性能: ⭐⭐ 较慢 (可能使用了 CPU)")

print("\n" + "="*60)
if detector.is_gpu_available and elapsed < 50:
    print("✅ GPU 正常工作！")
elif detector.is_gpu_available and elapsed >= 50:
    print("⚠️ GPU 已启用但性能不佳，请检查配置")
else:
    print("❌ GPU 未启用，使用 CPU")
print("="*60)
