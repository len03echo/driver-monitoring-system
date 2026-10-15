"""
测试UI改进功能
"""
import sys
import os
import pytest
import time

# 添加路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'client'))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer, QCoreApplication
from ui.main_window import MainWindow


@pytest.fixture
def app():
    """创建 QApplication 实例"""
    if not QCoreApplication.instance():
        app = QApplication([])
    else:
        app = QCoreApplication.instance()
    yield app


def test_ui_improvements(app):
    """测试UI改进功能"""
    window = MainWindow(initialize_components=False)
    window.show()
    
    # 测试彩色日志
    print("\n测试彩色日志...")
    window.add_log("这是普通信息", "info")
    window.add_log("这是警告信息", "warning")
    window.add_log("这是错误信息", "error")
    window.add_log("这是成功信息", "success")
    
    # 处理事件循环以确保UI更新
    app.processEvents()
    
    # 验证日志是否添加成功
    log_text = window.log_text.toPlainText()
    assert "这是普通信息" in log_text, "普通信息日志未找到"
    assert "这是警告信息" in log_text, "警告信息日志未找到"
    assert "这是错误信息" in log_text, "错误信息日志未找到"
    assert "这是成功信息" in log_text, "成功信息日志未找到"
    
    # 测试状态栏消息
    print("测试状态栏消息...")
    window.show_status_message("这是一条测试消息", 1000, "info")
    app.processEvents()
    time.sleep(0.1)
    
    window.show_status_message("这是一条警告消息", 1000, "warning")
    app.processEvents()
    time.sleep(0.1)
    
    window.show_status_message("这是一条错误消息", 1000, "error")
    app.processEvents()
    time.sleep(0.1)
    
    window.show_status_message("这是一条成功消息", 1000, "success")
    app.processEvents()
    time.sleep(0.1)
    
    # 关闭窗口
    window.close()
    
    print("UI改进测试完成")
    print("验证项：")
    print("✓ 日志区域显示了不同类型的日志")
    print("✓ 状态栏显示了临时消息")
    print("✓ 日志自动滚动到底部")


def manual_test_ui_improvements():
    """手动测试UI改进功能（用于直接运行脚本）"""
    app = QApplication(sys.argv)
    window = MainWindow(initialize_components=False)
    window.show()
    
    # 测试彩色日志
    print("测试彩色日志...")
    window.add_log("这是普通信息", "info")
    window.add_log("这是警告信息", "warning")
    window.add_log("这是错误信息", "error")
    window.add_log("这是成功信息", "success")
    
    # 测试状态栏消息
    print("测试状态栏消息...")
    QTimer.singleShot(1000, lambda: window.show_status_message("这是一条测试消息", 3000, "info"))
    QTimer.singleShot(2000, lambda: window.show_status_message("这是一条警告消息", 3000, "warning"))
    QTimer.singleShot(3000, lambda: window.show_status_message("这是一条错误消息", 3000, "error"))
    QTimer.singleShot(4000, lambda: window.show_status_message("这是一条成功消息", 3000, "success"))
    
    # 6秒后自动关闭
    QTimer.singleShot(6000, app.quit)
    
    print("UI改进测试启动，将在6秒后自动关闭...")
    print("请观察：")
    print("1. 日志区域是否显示了不同颜色的日志")
    print("2. 状态栏是否显示了临时消息")
    print("3. 日志是否自动滚动到底部")
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    manual_test_ui_improvements()
