"""
Task-30：连续帧计数器单元测试

测试 BehaviorDetector 和 FatigueDetector 中连续帧计数逻辑的正确性。
不依赖 YOLO/MediaPipe 模型，直接测试计数器逻辑。
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class FrameCounter:
    """
    连续帧计数器（提取自 BehaviorDetector/FatigueDetector 的核心逻辑）
    用于单独测试计数器行为
    """

    def __init__(self, threshold: int):
        self.threshold = threshold
        self.counter = 0

    def update(self, detected: bool) -> bool:
        """
        更新计数器。
        :param detected: 当前帧是否检测到目标
        :return: 是否触发告警（恰好达到阈值时触发一次）
        """
        if detected:
            self.counter += 1
            if self.counter == self.threshold:
                self.counter = 0  # 触发后重置，防止持续触发
                return True
        else:
            self.counter = 0
        return False

    def reset(self):
        self.counter = 0


class TestFrameCounter:
    """测试连续帧计数器逻辑"""

    def test_trigger_at_threshold(self):
        """连续检测到阈值帧数时触发告警"""
        counter = FrameCounter(threshold=10)
        triggered = False
        for i in range(10):
            result = counter.update(True)
            if result:
                triggered = True
        assert triggered, "连续10帧应触发告警"

    def test_no_trigger_before_threshold(self):
        """未达到阈值时不触发告警"""
        counter = FrameCounter(threshold=10)
        for i in range(9):
            result = counter.update(True)
            assert not result, f"第{i+1}帧不应触发告警"

    def test_reset_on_miss(self):
        """中断检测后计数器应重置"""
        counter = FrameCounter(threshold=10)
        # 检测9帧
        for _ in range(9):
            counter.update(True)
        assert counter.counter == 9
        # 中断一帧
        counter.update(False)
        assert counter.counter == 0, "中断后计数器应重置为0"

    def test_no_trigger_after_interrupt(self):
        """中断后重新计数，不应在原计数基础上累加"""
        counter = FrameCounter(threshold=10)
        # 检测9帧后中断
        for _ in range(9):
            counter.update(True)
        counter.update(False)
        # 再检测9帧，不应触发
        triggered = False
        for _ in range(9):
            if counter.update(True):
                triggered = True
        assert not triggered, "中断后重新计数，9帧不应触发"

    def test_trigger_only_once_per_cycle(self):
        """达到阈值后重置，不应连续触发"""
        counter = FrameCounter(threshold=5)
        trigger_count = 0
        # 连续检测20帧
        for _ in range(20):
            if counter.update(True):
                trigger_count += 1
        # 20帧 / 5阈值 = 4次触发
        assert trigger_count == 4, f"20帧应触发4次，实际: {trigger_count}"

    def test_reset_method(self):
        """reset() 方法应将计数器归零"""
        counter = FrameCounter(threshold=10)
        for _ in range(7):
            counter.update(True)
        assert counter.counter == 7
        counter.reset()
        assert counter.counter == 0

    def test_threshold_1(self):
        """阈值为1时，每帧检测到都触发"""
        counter = FrameCounter(threshold=1)
        assert counter.update(True) is True
        assert counter.update(True) is True

    def test_threshold_20_eye_closed(self):
        """模拟闭眼检测：阈值20帧"""
        counter = FrameCounter(threshold=20)
        trigger_count = 0
        for _ in range(20):
            if counter.update(True):
                trigger_count += 1
        assert trigger_count == 1, "连续20帧应触发1次闭眼告警"

    def test_threshold_15_yawning(self):
        """模拟哈欠检测：阈值15帧"""
        counter = FrameCounter(threshold=15)
        trigger_count = 0
        for _ in range(15):
            if counter.update(True):
                trigger_count += 1
        assert trigger_count == 1, "连续15帧应触发1次哈欠告警"

    def test_counter_increments_correctly(self):
        """计数器应逐帧递增"""
        counter = FrameCounter(threshold=100)
        for i in range(1, 10):
            counter.update(True)
            assert counter.counter == i, f"第{i}帧后计数器应为{i}"

    def test_false_detection_resets(self):
        """未检测到目标时计数器应归零"""
        counter = FrameCounter(threshold=10)
        for _ in range(5):
            counter.update(True)
        counter.update(False)
        assert counter.counter == 0

    def test_alternating_detection(self):
        """交替检测不应触发告警"""
        counter = FrameCounter(threshold=5)
        triggered = False
        for _ in range(20):
            counter.update(True)
            if counter.update(False):
                triggered = True
        assert not triggered, "交替检测不应触发告警"


class TestMultiClassFrameCounter:
    """测试多类别连续帧计数器（模拟 BehaviorDetector）"""

    def setup_method(self):
        """初始化多类别计数器"""
        self.threshold = 10
        self.counters = {"phone": 0, "cup": 0, "smoking": 0}

    def update_counters(self, detected_classes):
        """更新多类别计数器，返回触发的类别列表"""
        triggered = []
        for cls in self.counters:
            if cls in detected_classes:
                self.counters[cls] += 1
                if self.counters[cls] == self.threshold:
                    triggered.append(cls)
                    self.counters[cls] = 0
            else:
                self.counters[cls] = 0
        return triggered

    def test_single_class_trigger(self):
        """单类别连续检测触发"""
        for _ in range(9):
            self.update_counters({"phone"})
        result = self.update_counters({"phone"})
        assert "phone" in result

    def test_multiple_class_trigger(self):
        """多类别同时触发"""
        for _ in range(9):
            self.update_counters({"phone", "smoking"})
        result = self.update_counters({"phone", "smoking"})
        assert "phone" in result
        assert "smoking" in result

    def test_independent_counters(self):
        """各类别计数器相互独立"""
        # phone 检测5帧后中断
        for _ in range(5):
            self.update_counters({"phone"})
        self.update_counters(set())  # 中断
        # cup 继续检测10帧
        triggered = []
        for _ in range(10):
            triggered.extend(self.update_counters({"cup"}))
        assert "cup" in triggered
        assert "phone" not in triggered

    def test_reset_all_counters(self):
        """重置所有计数器"""
        for _ in range(5):
            self.update_counters({"phone", "cup", "smoking"})
        # 重置
        for cls in self.counters:
            self.counters[cls] = 0
        assert all(v == 0 for v in self.counters.values())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
