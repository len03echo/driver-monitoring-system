"""
测试嘴巴关键点修复

验证：
1. MOUTH_POINTS 包含上下唇关键点
2. MAR 计算使用正确的关键点
3. 绘制时显示完整的嘴巴轮廓
"""
import sys
import os

# 添加路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'client'))

from core.fatigue_detector import FatigueDetector


def test_mouth_points_definition():
    """测试嘴巴关键点定义"""
    detector = FatigueDetector()
    
    # 验证 MOUTH_POINTS 有8个点
    assert len(detector.MOUTH_POINTS) == 8, f"MOUTH_POINTS 应该有8个点，实际有 {len(detector.MOUTH_POINTS)} 个"
    
    # 验证包含左右嘴角
    assert 61 in detector.MOUTH_POINTS, "应该包含左嘴角关键点 61"
    assert 291 in detector.MOUTH_POINTS, "应该包含右嘴角关键点 291"
    
    # 验证包含上唇关键点（13, 14, 312）
    upper_lip_points = [13, 14, 312]
    for point in upper_lip_points:
        assert point in detector.MOUTH_POINTS, f"应该包含上唇关键点 {point}"
    
    # 验证包含下唇关键点（17, 18, 200）
    lower_lip_points = [17, 18, 200]
    for point in lower_lip_points:
        assert point in detector.MOUTH_POINTS, f"应该包含下唇关键点 {point}"
    
    print("✓ MOUTH_POINTS 定义正确")
    print(f"  关键点索引: {detector.MOUTH_POINTS}")
    print(f"  左嘴角: 61, 右嘴角: 291")
    print(f"  上唇: 13, 14, 312")
    print(f"  下唇: 17, 18, 200")


def test_mouth_outer_points():
    """测试完整嘴巴轮廓关键点"""
    detector = FatigueDetector()
    
    # 验证 MOUTH_OUTER_POINTS 包含足够的点
    assert len(detector.MOUTH_OUTER_POINTS) > 10, "MOUTH_OUTER_POINTS 应该包含足够多的点来绘制完整轮廓"
    
    # 验证包含左右嘴角
    assert 61 in detector.MOUTH_OUTER_POINTS, "轮廓应该包含左嘴角"
    assert 291 in detector.MOUTH_OUTER_POINTS, "轮廓应该包含右嘴角"
    
    print("✓ MOUTH_OUTER_POINTS 定义正确")
    print(f"  总共 {len(detector.MOUTH_OUTER_POINTS)} 个关键点")


def test_mar_calculation_with_new_points():
    """测试使用新关键点的 MAR 计算"""
    detector = FatigueDetector()
    
    # 测试闭嘴状态（所有点在同一水平线）
    closed_mouth = [
        (100, 200),  # 左嘴角 (61)
        (110, 200),  # 上唇 (13)
        (120, 200),  # 上唇 (14)
        (130, 200),  # 上唇 (312)
        (140, 200),  # 右嘴角 (291)
        (130, 200),  # 下唇 (17)
        (120, 200),  # 下唇 (18)
        (110, 200),  # 下唇 (200)
    ]
    
    mar_closed = detector._calculate_mar(closed_mouth)
    print(f"\n✓ 闭嘴状态 MAR: {mar_closed:.3f}")
    assert mar_closed < 0.1, f"闭嘴状态 MAR 应该接近 0，实际为 {mar_closed:.3f}"
    
    # 测试张嘴状态（上下唇有明显距离）
    open_mouth = [
        (100, 200),  # 左嘴角 (61)
        (110, 180),  # 上唇 (13) - 向上
        (120, 175),  # 上唇 (14) - 向上
        (130, 180),  # 上唇 (312) - 向上
        (140, 200),  # 右嘴角 (291)
        (130, 220),  # 下唇 (17) - 向下
        (120, 225),  # 下唇 (18) - 向下
        (110, 220),  # 下唇 (200) - 向下
    ]
    
    mar_open = detector._calculate_mar(open_mouth)
    print(f"✓ 张嘴状态 MAR: {mar_open:.3f}")
    assert mar_open > 0.5, f"张嘴状态 MAR 应该大于 0.5，实际为 {mar_open:.3f}"
    
    print(f"✓ MAR 计算正确，能够区分闭嘴和张嘴状态")


if __name__ == "__main__":
    print("=" * 60)
    print("测试嘴巴关键点修复")
    print("=" * 60)
    
    test_mouth_points_definition()
    print()
    test_mouth_outer_points()
    print()
    test_mar_calculation_with_new_points()
    
    print("\n" + "=" * 60)
    print("所有测试通过！✓")
    print("=" * 60)
