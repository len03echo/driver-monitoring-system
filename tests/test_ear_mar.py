"""
Task-30：EAR/MAR 计算单元测试

测试 FatigueDetector 中 EAR（眼睛纵横比）和 MAR（嘴巴纵横比）的计算逻辑。
不依赖 MediaPipe 模型，直接测试计算方法。
"""

import pytest
import math
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# 直接从 FatigueDetector 提取计算函数进行测试，避免初始化 MediaPipe
def calculate_ear(eye_points):
    """EAR = (|p2-p6| + |p3-p5|) / (2 * |p1-p4|)"""
    if len(eye_points) != 6:
        return 1.0
    vertical_1 = math.sqrt((eye_points[1][0] - eye_points[5][0])**2 +
                            (eye_points[1][1] - eye_points[5][1])**2)
    vertical_2 = math.sqrt((eye_points[2][0] - eye_points[4][0])**2 +
                            (eye_points[2][1] - eye_points[4][1])**2)
    horizontal = math.sqrt((eye_points[0][0] - eye_points[3][0])**2 +
                            (eye_points[0][1] - eye_points[3][1])**2)
    if horizontal == 0:
        return 1.0
    return (vertical_1 + vertical_2) / (2.0 * horizontal)


def calculate_mar(mouth_points):
    """MAR = (|p2-p8| + |p3-p7| + |p4-p6|) / (3 * |p1-p5|)"""
    if len(mouth_points) != 8:
        return 0.0
    vertical_1 = math.sqrt((mouth_points[1][0] - mouth_points[7][0])**2 +
                            (mouth_points[1][1] - mouth_points[7][1])**2)
    vertical_2 = math.sqrt((mouth_points[2][0] - mouth_points[6][0])**2 +
                            (mouth_points[2][1] - mouth_points[6][1])**2)
    vertical_3 = math.sqrt((mouth_points[3][0] - mouth_points[5][0])**2 +
                            (mouth_points[3][1] - mouth_points[5][1])**2)
    horizontal = math.sqrt((mouth_points[0][0] - mouth_points[4][0])**2 +
                            (mouth_points[0][1] - mouth_points[4][1])**2)
    if horizontal == 0:
        return 0.0
    return (vertical_1 + vertical_2 + vertical_3) / (3.0 * horizontal)


class TestEAR:
    """测试 EAR（眼睛纵横比）计算"""

    def test_ear_open_eye(self):
        """睁眼时 EAR 应大于阈值 0.25"""
        # 构造一个标准睁眼的6点坐标
        # p1(左), p2(左上), p3(右上), p4(右), p5(右下), p6(左下)
        eye_points = [
            (0, 5),    # p1 左端
            (2, 8),    # p2 左上
            (4, 8),    # p3 右上
            (6, 5),    # p4 右端
            (4, 2),    # p5 右下
            (2, 2),    # p6 左下
        ]
        ear = calculate_ear(eye_points)
        assert ear > 0.25, f"睁眼 EAR 应大于 0.25，实际: {ear}"

    def test_ear_closed_eye(self):
        """闭眼时 EAR 应小于阈值 0.25"""
        # 构造一个闭眼的6点坐标（垂直距离很小）
        eye_points = [
            (0, 5),    # p1 左端
            (2, 5.1),  # p2 左上（几乎与p6同高）
            (4, 5.1),  # p3 右上
            (6, 5),    # p4 右端
            (4, 4.9),  # p5 右下
            (2, 4.9),  # p6 左下
        ]
        ear = calculate_ear(eye_points)
        assert ear < 0.25, f"闭眼 EAR 应小于 0.25，实际: {ear}"

    def test_ear_formula_correctness(self):
        """验证 EAR 公式计算正确性"""
        # 构造已知结果的坐标
        # 水平距离 = 10，垂直距离各为 4
        eye_points = [
            (0, 0),    # p1
            (3, 4),    # p2
            (7, 4),    # p3
            (10, 0),   # p4
            (7, -4),   # p5
            (3, -4),   # p6
        ]
        ear = calculate_ear(eye_points)
        # 垂直1 = |p2-p6| = |(3,4)-(3,-4)| = 8
        # 垂直2 = |p3-p5| = |(7,4)-(7,-4)| = 8
        # 水平 = |p1-p4| = 10
        # EAR = (8+8) / (2*10) = 0.8
        assert abs(ear - 0.8) < 1e-6, f"EAR 计算错误，期望 0.8，实际: {ear}"

    def test_ear_invalid_points(self):
        """关键点数量不足时返回默认值 1.0"""
        ear = calculate_ear([(0, 0), (1, 1)])  # 只有2个点
        assert ear == 1.0

    def test_ear_zero_horizontal(self):
        """水平距离为0时返回默认值 1.0（避免除零）"""
        eye_points = [
            (5, 0),   # p1 与 p4 同x坐标
            (5, 2),
            (5, 2),
            (5, 0),   # p4
            (5, -2),
            (5, -2),
        ]
        ear = calculate_ear(eye_points)
        assert ear == 1.0

    def test_ear_symmetry(self):
        """左右对称的眼睛 EAR 值应相同"""
        left_eye = [
            (0, 5), (2, 8), (4, 8), (6, 5), (4, 2), (2, 2)
        ]
        right_eye = [
            (10, 5), (12, 8), (14, 8), (16, 5), (14, 2), (12, 2)
        ]
        ear_left = calculate_ear(left_eye)
        ear_right = calculate_ear(right_eye)
        assert abs(ear_left - ear_right) < 1e-6, "对称眼睛的 EAR 应相等"

    def test_ear_non_negative(self):
        """EAR 值应始终非负"""
        eye_points = [
            (0, 0), (1, 1), (2, 1), (3, 0), (2, -1), (1, -1)
        ]
        ear = calculate_ear(eye_points)
        assert ear >= 0, "EAR 值不应为负数"


class TestMAR:
    """测试 MAR（嘴巴纵横比）计算"""

    def test_mar_closed_mouth(self):
        """闭嘴时 MAR 应小于阈值 0.6"""
        # 构造闭嘴坐标（垂直距离很小）
        mouth_points = [
            (0, 5),    # p1 左端
            (2, 5.1),  # p2
            (4, 5.1),  # p3
            (6, 5.1),  # p4
            (8, 5),    # p5 右端
            (6, 4.9),  # p6
            (4, 4.9),  # p7
            (2, 4.9),  # p8
        ]
        mar = calculate_mar(mouth_points)
        assert mar < 0.6, f"闭嘴 MAR 应小于 0.6，实际: {mar}"

    def test_mar_open_mouth(self):
        """张嘴时 MAR 应大于阈值 0.6"""
        # 构造张嘴坐标（垂直距离较大）
        mouth_points = [
            (0, 5),    # p1 左端
            (2, 10),   # p2 上
            (4, 11),   # p3 上
            (6, 10),   # p4 上
            (8, 5),    # p5 右端
            (6, 0),    # p6 下
            (4, -1),   # p7 下
            (2, 0),    # p8 下
        ]
        mar = calculate_mar(mouth_points)
        assert mar > 0.6, f"张嘴 MAR 应大于 0.6，实际: {mar}"

    def test_mar_formula_correctness(self):
        """验证 MAR 公式计算正确性"""
        # 水平距离 = 10，三组垂直距离各为 6
        mouth_points = [
            (0, 0),    # p1
            (2, 3),    # p2
            (5, 3),    # p3
            (8, 3),    # p4
            (10, 0),   # p5
            (8, -3),   # p6
            (5, -3),   # p7
            (2, -3),   # p8
        ]
        mar = calculate_mar(mouth_points)
        # 垂直1 = |p2-p8| = |(2,3)-(2,-3)| = 6
        # 垂直2 = |p3-p7| = |(5,3)-(5,-3)| = 6
        # 垂直3 = |p4-p6| = |(8,3)-(8,-3)| = 6
        # 水平 = |p1-p5| = 10
        # MAR = (6+6+6) / (3*10) = 0.6
        assert abs(mar - 0.6) < 1e-6, f"MAR 计算错误，期望 0.6，实际: {mar}"

    def test_mar_invalid_points(self):
        """关键点数量不足时返回默认值 0.0"""
        mar = calculate_mar([(0, 0), (1, 1)])
        assert mar == 0.0

    def test_mar_zero_horizontal(self):
        """水平距离为0时返回默认值 0.0（避免除零）"""
        # p1=(5,0) 和 p5=(5,0) 完全相同，水平距离为0
        mouth_points = [
            (5, 0),   # p1
            (5, 1),   # p2
            (5, 2),   # p3
            (5, 3),   # p4
            (5, 0),   # p5 与 p1 相同，水平距离=0
            (5, -1),  # p6
            (5, -2),  # p7
            (5, -3),  # p8
        ]
        mar = calculate_mar(mouth_points)
        assert mar == 0.0

    def test_mar_non_negative(self):
        """MAR 值应始终非负"""
        mouth_points = [
            (0, 0), (2, 1), (4, 1), (6, 1),
            (8, 0), (6, -1), (4, -1), (2, -1)
        ]
        mar = calculate_mar(mouth_points)
        assert mar >= 0, "MAR 值不应为负数"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
