"""
测试行为检测器的类别映射
验证新训练的模型是否正确识别 smoke/phone/drink
"""

import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(__file__))

from client.core.behavior_detector import BehaviorDetector

def test_class_mapping():
    """测试类别映射"""
    print("=" * 60)
    print("测试行为检测器类别映射")
    print("=" * 60)
    
    # 检查类别映射
    print("\n1. 类别ID到名称映射:")
    print(f"   CLASS_ID_TO_NAME = {BehaviorDetector.CLASS_ID_TO_NAME}")
    
    print("\n2. 类别危险等级映射:")
    print(f"   CLASS_SEVERITY_MAP = {BehaviorDetector.CLASS_SEVERITY_MAP}")
    
    print("\n3. 预期行为:")
    print("   - class_id=0 (face) 会被过滤，不触发告警")
    print("   - class_id=1 (smoke) → 高危险 (high)")
    print("   - class_id=2 (phone) → 中危险 (medium)")
    print("   - class_id=3 (drink) → 低危险 (low)")
    
    print("\n4. 验证结果:")
    
    # 验证类别映射
    expected_mapping = {
        1: 'smoke',
        2: 'phone',
        3: 'drink'
    }
    
    if BehaviorDetector.CLASS_ID_TO_NAME == expected_mapping:
        print("   ✅ 类别映射正确")
    else:
        print("   ❌ 类别映射错误")
        return False
    
    # 验证危险等级
    expected_severity = {
        "smoke": "high",
        "phone": "medium",
        "drink": "low"
    }
    
    if BehaviorDetector.CLASS_SEVERITY_MAP == expected_severity:
        print("   ✅ 危险等级映射正确")
    else:
        print("   ❌ 危险等级映射错误")
        return False
    
    print("\n" + "=" * 60)
    print("✅ 所有测试通过！")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = test_class_mapping()
    sys.exit(0 if success else 1)
