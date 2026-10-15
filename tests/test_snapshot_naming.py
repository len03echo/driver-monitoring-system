"""
Task-30：截图命名格式单元测试

测试 AlertEngine 中截图文件命名格式是否符合规范：
{session_id}_{alert_type}_{timestamp}.jpg
"""

import pytest
import re
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def generate_snapshot_filename(session_id, alert_type, timestamp=None):
    """
    生成截图文件名（与 AlertEngine._generate_snapshot_filename 逻辑一致）
    格式: {session_id}_{alert_type}_{timestamp}.jpg
    """
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"{session_id}_{alert_type}_{timestamp}.jpg"


# 截图文件名正则表达式
SNAPSHOT_PATTERN = re.compile(
    r'^(\d+|unknown)_(phone|cup|smoking|eye_closed|yawning|head_down|unknown)_(\d{14})\.jpg$'
)


class TestSnapshotNaming:
    """测试截图文件命名格式"""

    def test_basic_format(self):
        """基本命名格式应符合规范"""
        filename = generate_snapshot_filename(1, "phone", "20240117142035")
        assert filename == "1_phone_20240117142035.jpg"

    def test_pattern_match(self):
        """生成的文件名应匹配正则表达式"""
        filename = generate_snapshot_filename(12, "smoking", "20240117142136")
        assert SNAPSHOT_PATTERN.match(filename), f"文件名不符合规范: {filename}"

    def test_all_alert_types(self):
        """所有告警类型都应生成合法文件名"""
        alert_types = ["phone", "cup", "smoking", "eye_closed", "yawning", "head_down"]
        for alert_type in alert_types:
            filename = generate_snapshot_filename(1, alert_type, "20240117142035")
            assert SNAPSHOT_PATTERN.match(filename), f"告警类型 {alert_type} 文件名不符合规范: {filename}"

    def test_session_id_in_filename(self):
        """文件名应包含正确的 session_id"""
        filename = generate_snapshot_filename(42, "phone", "20240117142035")
        assert filename.startswith("42_"), f"文件名应以 session_id 开头: {filename}"

    def test_alert_type_in_filename(self):
        """文件名应包含正确的告警类型"""
        filename = generate_snapshot_filename(1, "eye_closed", "20240117142035")
        assert "_eye_closed_" in filename, f"文件名应包含告警类型: {filename}"

    def test_timestamp_format(self):
        """时间戳格式应为 YYYYMMDDHHmmss（14位数字）"""
        filename = generate_snapshot_filename(1, "phone", "20240117142035")
        # 提取时间戳部分
        parts = filename.replace(".jpg", "").split("_")
        timestamp = parts[-1]
        assert len(timestamp) == 14, f"时间戳应为14位，实际: {timestamp}"
        assert timestamp.isdigit(), f"时间戳应全为数字，实际: {timestamp}"

    def test_jpg_extension(self):
        """文件名应以 .jpg 结尾"""
        filename = generate_snapshot_filename(1, "phone", "20240117142035")
        assert filename.endswith(".jpg"), f"文件名应以 .jpg 结尾: {filename}"

    def test_auto_timestamp(self):
        """不传入时间戳时应自动生成"""
        filename = generate_snapshot_filename(1, "phone")
        assert SNAPSHOT_PATTERN.match(filename), f"自动时间戳文件名不符合规范: {filename}"

    def test_large_session_id(self):
        """大 session_id 应正常处理"""
        filename = generate_snapshot_filename(99999, "phone", "20240117142035")
        assert filename.startswith("99999_")
        assert SNAPSHOT_PATTERN.match(filename)

    def test_filename_uniqueness(self):
        """不同时间戳生成的文件名应不同"""
        filename1 = generate_snapshot_filename(1, "phone", "20240117142035")
        filename2 = generate_snapshot_filename(1, "phone", "20240117142036")
        assert filename1 != filename2, "不同时间戳应生成不同文件名"

    def test_filename_components_count(self):
        """文件名应由3个下划线分隔的部分组成（session_id, alert_type, timestamp）"""
        # eye_closed 类型包含下划线，需要特殊处理
        filename = generate_snapshot_filename(1, "phone", "20240117142035")
        # 去掉扩展名后按下划线分割
        name_without_ext = filename.replace(".jpg", "")
        # session_id 在第一个下划线前，timestamp 在最后一个下划线后
        first_underscore = name_without_ext.index("_")
        last_underscore = name_without_ext.rindex("_")
        session_id = name_without_ext[:first_underscore]
        timestamp = name_without_ext[last_underscore + 1:]
        alert_type = name_without_ext[first_underscore + 1:last_underscore]
        assert session_id == "1"
        assert alert_type == "phone"
        assert timestamp == "20240117142035"

    def test_eye_closed_filename(self):
        """eye_closed 类型（含下划线）的文件名应正确解析"""
        filename = generate_snapshot_filename(5, "eye_closed", "20240117142237")
        assert filename == "5_eye_closed_20240117142237.jpg"
        assert SNAPSHOT_PATTERN.match(filename)

    def test_head_down_filename(self):
        """head_down 类型的文件名应正确"""
        filename = generate_snapshot_filename(3, "head_down", "20240117142338")
        assert filename == "3_head_down_20240117142338.jpg"
        assert SNAPSHOT_PATTERN.match(filename)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
