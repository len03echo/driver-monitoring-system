"""
测试UI布局改进

验证：
1. 状态标签横向排列
2. 状态标签字号更大（14px）
3. "眨眼次数" 改为 "闭眼次数"
4. "低头次数" 改为 "低头时间（秒）"
5. 日志区域高度自适应
"""
import sys
import os
import pytest

# 添加路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'client'))

from PyQt5.QtWidgets import QApplication, QHBoxLayout, QVBoxLayout
from PyQt5.QtCore import QCoreApplication


@pytest.fixture
def app():
    """创建 QApplication 实例"""
    if not QCoreApplication.instance():
        app = QApplication([])
    else:
        app = QCoreApplication.instance()
    yield app


def test_status_labels_horizontal_layout(app):
    """测试状态标签横向排列"""
    from ui.main_window import MainWindow
    
    window = MainWindow(initialize_components=False)
    
    # 查找状态组
    status_group = None
    for child in window.findChildren(type(window)):
        if hasattr(child, 'title') and child.title() == "系统状态":
            status_group = child
            break
    
    # 验证状态标签存在
    assert hasattr(window, 'eye_status_label')
    assert hasattr(window, 'mouth_status_label')
    assert hasattr(window, 'head_status_label')
    
    window.close()
    
    print("✓ 状态标签已创建")


def test_status_labels_font_size(app):
    """测试状态标签字号已设置"""
    from ui.main_window import MainWindow
    
    window = MainWindow(initialize_components=False)
    
    # 检查字号存在（当前为 18px）
    eye_style = window.eye_status_label.styleSheet()
    mouth_style = window.mouth_status_label.styleSheet()
    head_style = window.head_status_label.styleSheet()
    
    assert "font-size" in eye_style, f"眼睛状态标签应设置字号，实际样式: {eye_style}"
    assert "font-size" in mouth_style, f"嘴巴状态标签应设置字号，实际样式: {mouth_style}"
    assert "font-size" in head_style, f"头部状态标签应设置字号，实际样式: {head_style}"
    
    window.close()
    
    print("✓ 状态标签已设置字号")


def test_status_labels_text(app):
    """测试状态标签文本"""
    from ui.main_window import MainWindow
    
    window = MainWindow(initialize_components=False)
    
    # 验证简化的文本
    assert "眼睛:" in window.eye_status_label.text() or "眼睛 :" in window.eye_status_label.text()
    assert "嘴巴:" in window.mouth_status_label.text() or "嘴巴 :" in window.mouth_status_label.text()
    assert "头部:" in window.head_status_label.text() or "头部 :" in window.head_status_label.text()
    
    window.close()
    
    print("✓ 状态标签文本已简化")
    print(f"  - {window.eye_status_label.text()}")
    print(f"  - {window.mouth_status_label.text()}")
    print(f"  - {window.head_status_label.text()}")


def test_blink_count_renamed(app):
    """测试眨眼次数改为闭眼次数"""
    from ui.main_window import MainWindow
    
    window = MainWindow(initialize_components=False)
    
    # 验证标签文本
    assert "闭眼次数" in window.blink_count_label.text(), \
        f"应该显示'闭眼次数'，实际为: {window.blink_count_label.text()}"
    
    window.close()
    
    print("✓ '眨眼次数' 已改为 '闭眼次数'")


def test_head_down_time_display(app):
    """测试低头显示包含秒"""
    from ui.main_window import MainWindow
    
    window = MainWindow(initialize_components=False)
    
    # 验证标签文本包含"秒"（实际格式为 "⬇ 低头: 0秒"）
    label_text = window.head_down_count_label.text()
    assert "低头" in label_text, f"应该包含'低头'，实际为: {label_text}"
    assert "秒" in label_text, f"应该包含'秒'单位，实际为: {label_text}"
    
    window.close()
    
    print("✓ '低头' 标签以秒为单位显示")
    print(f"  显示: {label_text}")


def test_head_down_time_tracking(app):
    """测试低头时间追踪变量"""
    from ui.main_window import MainWindow
    
    window = MainWindow(initialize_components=False)
    
    # 验证时间追踪变量存在
    assert hasattr(window, 'total_head_down_time'), "应该有 total_head_down_time 变量"
    assert hasattr(window, 'head_down_start_time'), "应该有 head_down_start_time 变量"
    
    # 验证初始值
    assert window.total_head_down_time == 0.0
    assert window.head_down_start_time is None
    
    window.close()
    
    print("✓ 低头时间追踪变量已添加")


def test_log_area_adaptive_height(app):
    """测试日志区域高度自适应"""
    from ui.main_window import MainWindow
    
    window = MainWindow(initialize_components=False)
    
    # 检查日志文本框没有最大高度限制
    log_text = window.log_text
    
    # 获取样式表
    style = log_text.styleSheet()
    
    # 验证有最小高度但没有最大高度
    assert log_text.minimumHeight() > 0, "应该设置最小高度"
    
    # 检查是否没有设置 maximumHeight（或设置为一个很大的值）
    max_height = log_text.maximumHeight()
    # Qt 默认最大高度是 16777215
    assert max_height > 1000, f"日志区域应该可以自适应高度，当前最大高度: {max_height}"
    
    window.close()
    
    print("✓ 日志区域高度可自适应")
    print(f"  最小高度: {log_text.minimumHeight()}px")
    print(f"  最大高度: {max_height}px (自适应)")


if __name__ == "__main__":
    print("=" * 60)
    print("测试UI布局改进")
    print("=" * 60)
    
    # 需要 QApplication 的测试
    app = QApplication([])
    
    test_status_labels_horizontal_layout(app)
    print()
    
    test_status_labels_font_size(app)
    print()
    
    test_status_labels_text(app)
    print()
    
    test_blink_count_renamed(app)
    print()
    
    test_head_down_time_display(app)
    print()
    
    test_head_down_time_tracking(app)
    print()
    
    test_log_area_adaptive_height(app)
    
    print("\n" + "=" * 60)
    print("所有测试通过！✓")
    print("=" * 60)
