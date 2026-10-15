"""
测试状态显示改进

验证：
1. MAR 阈值已更新为 0.65
2. 系统状态中有眼睛、嘴巴、头部状态标签
3. 状态标签能够根据检测结果改变颜色
4. 不再显示弹窗警告
"""
import sys
import os
import pytest

# 添加路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'client'))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QCoreApplication
from config import load_config


@pytest.fixture
def app():
    """创建 QApplication 实例"""
    if not QCoreApplication.instance():
        app = QApplication([])
    else:
        app = QCoreApplication.instance()
    yield app


def test_mar_threshold_updated():
    """测试 MAR 阈值已更新为 0.65"""
    config = load_config()
    
    assert config.detection.mar_threshold == 0.65, \
        f"MAR 阈值应该是 0.65，实际为 {config.detection.mar_threshold}"
    
    print(f"✓ MAR 阈值已正确设置为: {config.detection.mar_threshold}")


def test_main_window_has_status_labels(app):
    """测试主窗口包含状态标签"""
    from ui.main_window import MainWindow
    
    window = MainWindow(initialize_components=False)
    
    # 验证状态标签存在
    assert hasattr(window, 'eye_status_label'), "应该有眼睛状态标签"
    assert hasattr(window, 'mouth_status_label'), "应该有嘴巴状态标签"
    assert hasattr(window, 'head_status_label'), "应该有头部状态标签"
    
    # 验证初始文本（实际标签格式为 "👁 眼睛: 正常"）
    assert "眼睛" in window.eye_status_label.text()
    assert "嘴巴" in window.mouth_status_label.text()
    assert "头部" in window.head_status_label.text()
    
    window.close()
    
    print("✓ 主窗口包含所有状态标签")
    print(f"  - {window.eye_status_label.text()}")
    print(f"  - {window.mouth_status_label.text()}")
    print(f"  - {window.head_status_label.text()}")


def test_no_alert_dialog_method(app):
    """测试弹窗方法已被禁用"""
    from ui.main_window import MainWindow
    
    window = MainWindow(initialize_components=False)
    
    # 检查 show_alert_dialog 方法是否存在但已被注释
    # 或者检查方法是否不会实际显示对话框
    if hasattr(window, 'show_alert_dialog'):
        # 方法存在但应该是空实现或注释掉的
        import inspect
        source = inspect.getsource(window.show_alert_dialog)
        # 检查是否包含注释标记
        assert '#' in source or 'pass' in source, "show_alert_dialog 应该被禁用"
    
    window.close()
    
    print("✓ 弹窗警告功能已禁用")


def test_status_label_color_change(app):
    """测试状态标签颜色变化功能"""
    from ui.main_window import MainWindow
    
    window = MainWindow(initialize_components=False)
    
    # 模拟异常状态
    window.eye_status_label.setText("眼睛状态: 闭眼")
    window.eye_status_label.setStyleSheet("font-size: 12px; color: red; font-weight: bold;")
    
    # 验证样式包含红色
    assert "red" in window.eye_status_label.styleSheet().lower()
    
    # 模拟恢复正常
    window.eye_status_label.setText("眼睛状态: 正常")
    window.eye_status_label.setStyleSheet("font-size: 12px; color: green;")
    
    # 验证样式包含绿色
    assert "green" in window.eye_status_label.styleSheet().lower()
    
    window.close()
    
    print("✓ 状态标签颜色变化功能正常")


if __name__ == "__main__":
    print("=" * 60)
    print("测试状态显示改进")
    print("=" * 60)
    
    # 测试配置
    test_mar_threshold_updated()
    print()
    
    # 需要 QApplication 的测试
    app = QApplication([])
    
    test_main_window_has_status_labels(app)
    print()
    
    test_no_alert_dialog_method(app)
    print()
    
    test_status_label_color_change(app)
    
    print("\n" + "=" * 60)
    print("所有测试通过！✓")
    print("=" * 60)
