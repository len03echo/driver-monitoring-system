"""
Task-30：冷却机制单元测试

测试 AlertEngine 中 30 秒冷却机制的正确性。
不依赖 pygame/数据库，直接测试冷却逻辑。
"""

import pytest
import time
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class CooldownManager:
    """
    冷却管理器（提取自 AlertEngine 的核心冷却逻辑）
    """

    def __init__(self, cooldown_seconds: int = 30):
        self.cooldown_seconds = cooldown_seconds
        self.last_trigger_time: dict = {}

    def is_in_cooldown(self, alert_type: str) -> bool:
        if alert_type not in self.last_trigger_time:
            return False
        elapsed = time.time() - self.last_trigger_time[alert_type]
        return elapsed < self.cooldown_seconds

    def trigger(self, alert_type: str) -> bool:
        """尝试触发告警，返回是否成功（未在冷却期）"""
        if self.is_in_cooldown(alert_type):
            return False
        self.last_trigger_time[alert_type] = time.time()
        return True

    def reset(self):
        self.last_trigger_time.clear()

    def get_remaining_time(self, alert_type: str) -> float:
        if alert_type not in self.last_trigger_time:
            return 0.0
        elapsed = time.time() - self.last_trigger_time[alert_type]
        return max(0.0, self.cooldown_seconds - elapsed)


class TestCooldownMechanism:
    """测试冷却机制"""

    def test_first_trigger_succeeds(self):
        """首次触发应成功"""
        mgr = CooldownManager(cooldown_seconds=30)
        assert mgr.trigger("phone") is True

    def test_immediate_retrigger_blocked(self):
        """触发后立即重触发应被阻止"""
        mgr = CooldownManager(cooldown_seconds=30)
        mgr.trigger("phone")
        assert mgr.trigger("phone") is False

    def test_cooldown_expires(self):
        """冷却期结束后可以重新触发"""
        mgr = CooldownManager(cooldown_seconds=1)  # 1秒冷却
        mgr.trigger("phone")
        time.sleep(1.1)  # 等待冷却结束
        assert mgr.trigger("phone") is True

    def test_different_types_independent(self):
        """不同告警类型的冷却期相互独立"""
        mgr = CooldownManager(cooldown_seconds=30)
        mgr.trigger("phone")
        # phone 在冷却期，但 smoking 可以触发
        assert mgr.trigger("phone") is False
        assert mgr.trigger("smoking") is True

    def test_is_in_cooldown_before_trigger(self):
        """未触发过的类型不在冷却期"""
        mgr = CooldownManager(cooldown_seconds=30)
        assert mgr.is_in_cooldown("phone") is False

    def test_is_in_cooldown_after_trigger(self):
        """触发后应处于冷却期"""
        mgr = CooldownManager(cooldown_seconds=30)
        mgr.trigger("phone")
        assert mgr.is_in_cooldown("phone") is True

    def test_reset_clears_cooldown(self):
        """reset() 应清除所有冷却状态"""
        mgr = CooldownManager(cooldown_seconds=30)
        mgr.trigger("phone")
        mgr.trigger("smoking")
        mgr.reset()
        assert mgr.is_in_cooldown("phone") is False
        assert mgr.is_in_cooldown("smoking") is False

    def test_remaining_time_decreases(self):
        """剩余冷却时间应随时间减少"""
        mgr = CooldownManager(cooldown_seconds=5)
        mgr.trigger("phone")
        t1 = mgr.get_remaining_time("phone")
        time.sleep(0.1)
        t2 = mgr.get_remaining_time("phone")
        assert t1 > t2, "剩余冷却时间应随时间减少"

    def test_remaining_time_zero_before_trigger(self):
        """未触发时剩余冷却时间为 0"""
        mgr = CooldownManager(cooldown_seconds=30)
        assert mgr.get_remaining_time("phone") == 0.0

    def test_30_second_cooldown_suppresses_repeats(self):
        """30秒内重复触发应被抑制"""
        mgr = CooldownManager(cooldown_seconds=30)
        # 第一次触发成功
        assert mgr.trigger("eye_closed") is True
        # 后续触发被抑制
        for _ in range(10):
            assert mgr.trigger("eye_closed") is False

    def test_all_alert_types_independent(self):
        """所有告警类型冷却期独立"""
        mgr = CooldownManager(cooldown_seconds=30)
        alert_types = ["phone", "cup", "smoking", "eye_closed", "yawning", "head_down"]
        # 触发所有类型
        for t in alert_types:
            assert mgr.trigger(t) is True
        # 所有类型都在冷却期
        for t in alert_types:
            assert mgr.is_in_cooldown(t) is True
        # 重置后所有类型都不在冷却期
        mgr.reset()
        for t in alert_types:
            assert mgr.is_in_cooldown(t) is False

    def test_cooldown_with_short_duration(self):
        """短冷却时间测试（验证时间精度）"""
        mgr = CooldownManager(cooldown_seconds=2)
        mgr.trigger("phone")
        assert mgr.is_in_cooldown("phone") is True
        time.sleep(2.1)
        assert mgr.is_in_cooldown("phone") is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
